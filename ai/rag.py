"""
RAG ligero: recuperación BM25 sobre el corpus de PractIA, sin dependencias.

Indexa el banco de preguntas de entrevista (con la pista de lo que busca el
entrevistador) y las respuestas de referencia de los casos. El evaluador usa los
fragmentos más parecidos al caso y a la respuesta del candidato como material de
apoyo (retrieval-augmented generation): criterios de entrevistadores reales y
casos similares, en vez de depender solo de lo que el LLM recuerda.

Es deliberadamente simple (BM25 sobre palabras, sin embeddings) para no sumar
torch ni una base vectorial al deploy. El RAG con memorias anuales y ChromaDB
queda como ampliación (ver requirements-rag.txt).
"""
from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

AI_DIR = Path(__file__).parent

STOPWORDS = frozenset(
    "a al algo ante antes como con contra cual cuando de del desde donde e el ella ellos en entre era es esa ese eso esta este esto "
    "fue ha han hay la las le les lo los mas me mi muy no nos o para pero por que se si sin sobre son su sus te tu un una uno unos y ya "
    "yo hoy sera ser tiene tienen puede pueden hacer hace".split()
)


@dataclass(frozen=True)
class Documento:
    id: str
    fuente: str  # p. ej. "Banco de preguntas · tecnica_banca" o "Caso similar"
    titulo: str
    texto: str


def tokenizar(texto: str) -> list[str]:
    """Minúsculas, sin tildes, sin stopwords y con una raíz tosca (plurales)."""
    ascii_ = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    tokens = []
    for t in re.findall(r"[a-z0-9]+", ascii_):
        if len(t) < 3 or t in STOPWORDS:
            continue
        if len(t) > 4 and t.endswith("es") and t[-3] in "dlrnz":  # ciudades -> ciudad, comisiones -> comision
            t = t[:-2]
        elif len(t) > 3 and t.endswith("s"):  # clientes -> cliente, tasas -> tasa
            t = t[:-1]
        tokens.append(t)
    return tokens


@lru_cache(maxsize=1)
def corpus() -> tuple[Documento, ...]:
    """Preguntas del banco (con su hint) y casos (con su respuesta de referencia)."""
    docs: list[Documento] = []
    for path in sorted((AI_DIR / "questions").glob("*.json")):
        for i, q in enumerate(json.loads(path.read_text(encoding="utf-8"))):
            docs.append(Documento(
                id=f"pregunta:{path.stem}:{i}",
                fuente=f"Banco de preguntas · {path.stem}",
                titulo=q["pregunta"],
                texto=f"Qué busca el entrevistador: {q['hint']}",
            ))
    for path in sorted((AI_DIR / "cases").glob("*.json")):
        c = json.loads(path.read_text(encoding="utf-8"))
        referencia = c.get("respuesta_referencia") or c.get("pista_respuesta_modelo", "")
        docs.append(Documento(
            id=f"caso:{c['id']}",
            fuente="Caso similar",
            titulo=f"{c['company']} — {c['title']}",
            texto=f"Temas: {'; '.join(c.get('temas_evaluados', []))}. Referencia: {referencia}",
        ))
    return tuple(docs)


class BM25:
    """BM25 clásico (k1=1.5, b=0.75) sobre una lista de documentos."""

    def __init__(self, docs: tuple[Documento, ...], k1: float = 1.5, b: float = 0.75):
        self.docs = docs
        self.k1, self.b = k1, b
        self.tf = [Counter(tokenizar(f"{d.titulo} {d.texto}")) for d in docs]
        self.largo = [sum(tf.values()) for tf in self.tf]
        self.promedio = (sum(self.largo) / len(docs)) if docs else 0.0
        df: Counter = Counter()
        for tf in self.tf:
            df.update(tf.keys())
        n = len(docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def puntajes(self, consulta: str) -> list[float]:
        terminos = Counter(tokenizar(consulta))
        resultado = []
        for tf, largo in zip(self.tf, self.largo):
            s = 0.0
            for t in terminos:
                f = tf.get(t, 0)
                if not f:
                    continue
                denom = f + self.k1 * (1 - self.b + self.b * largo / (self.promedio or 1))
                s += self.idf[t] * f * (self.k1 + 1) / denom
            resultado.append(s)
        return resultado


@lru_cache(maxsize=1)
def _indice() -> BM25:
    return BM25(corpus())


def recuperar(consulta: str, k: int = 3, excluir_caso: str | None = None,
              solo_preguntas: bool = False) -> list[tuple[Documento, float]]:
    """Los `k` documentos más parecidos a la consulta, con su puntaje (excluye el propio caso).

    Con `solo_preguntas` se limita a las preguntas del banco (sin casos).
    """
    if k <= 0:
        return []
    indice = _indice()
    candidatos = [
        (doc, s) for doc, s in zip(indice.docs, indice.puntajes(consulta))
        if s > 0 and doc.id != f"caso:{excluir_caso}" and (not solo_preguntas or doc.id.startswith("pregunta:"))
    ]
    return sorted(candidatos, key=lambda x: -x[1])[:k]


def formatear(resultados: list[tuple[Documento, float]], max_chars: int = 280) -> list[str]:
    """Una línea por fragmento, recortada para cuidar los tokens del prompt."""
    lineas = []
    for doc, _ in resultados:
        texto = doc.texto if len(doc.texto) <= max_chars else doc.texto[:max_chars].rsplit(" ", 1)[0] + "…"
        lineas.append(f"[{doc.fuente}] {doc.titulo}. {texto}")
    return lineas
