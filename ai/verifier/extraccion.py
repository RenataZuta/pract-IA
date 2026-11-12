"""Paso 1: un LLM lista qué se puede comprobar (cuentas y hechos). No juzga ni calcula."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from loguru import logger
from pydantic import ValidationError

from ai.verifier.fuentes import extraer_json
from ai.verifier.llm import LlmVerificador
from ai.verifier.modelos import ChequeoNumerico, HechoReal
from ai.verifier.tablas import Tabla, describir

PROMPT = Path(__file__).resolve().parent.parent / "prompts" / "verificador_extraccion.md"
CACHE_DIR = Path(__file__).resolve().parent.parent / "audits" / ".cache"
MAX_CHEQUEOS, MAX_HECHOS = 14, 5


def texto_del_caso(case: dict) -> str:
    """Todo el texto del caso: contra él se comprueba que cada cita del modelo exista."""
    partes = [str(case.get(k, "")) for k in ("context", "prompt", "pista_respuesta_modelo", "respuesta_referencia")]
    partes += [f"{e['title']}\n{e['content']}" for e in case.get("exhibits") or []]
    return "\n".join(partes)


def texto_de_afirmaciones(case: dict) -> str:
    """Lo que el caso afirma (sin los anexos): contexto, pregunta, pista y referencia."""
    return "\n".join(str(case.get(k, "")) for k in ("context", "prompt", "pista_respuesta_modelo", "respuesta_referencia"))


def _mensaje_usuario(case: dict, tablas: list[Tabla]) -> str:
    return (
        f"# Caso {case['id']}: {case['title']} ({case['company']})\n\n"
        f"## Contexto\n{case['context']}\n\n## Pregunta\n{case['prompt']}\n\n"
        f"## Tablas de los anexos\n{describir(tablas) or '(sin tablas)'}\n\n"
        f"## Pista de respuesta modelo\n{case.get('pista_respuesta_modelo', '')}\n\n"
        f"## Respuesta de referencia\n{case.get('respuesta_referencia', '(no hay; usa la pista)')}\n"
    )


def extraer(case: dict, tablas: list[Tabla], llm: LlmVerificador, usar_cache: bool = True
            ) -> tuple[list[ChequeoNumerico], list[HechoReal], list[str]]:
    """Devuelve (chequeos, hechos, descartados). Un ítem mal formado se descarta y se reporta; no tumba el resto."""
    mensajes = [{"role": "system", "content": PROMPT.read_text(encoding="utf-8")},
                {"role": "user", "content": _mensaje_usuario(case, tablas)}]
    # Caché: la misma extracción (modelo + prompt + caso) no se vuelve a pagar; permite reevaluar sin gastar tokens.
    clave = hashlib.sha256(f"{llm.modelo}|{mensajes[0]['content']}|{mensajes[1]['content']}".encode()).hexdigest()[:20]
    ruta = CACHE_DIR / f"extraccion_{clave}.json"
    datos: dict | None = None
    if usar_cache and ruta.exists():
        try:
            en_cache = json.loads(ruta.read_text(encoding="utf-8"))
        except ValueError:
            en_cache = None
        if isinstance(en_cache, dict):  # una caché nunca se sirve sin validar su forma
            datos = en_cache
            logger.info("Extracción de {} desde caché", case["id"])
    for intento in (1, 2) if datos is None else ():
        respuesta = llm.completar(mensajes, json_mode=True, max_tokens=4500, estimado=6500, esfuerzo="medium")
        try:
            datos = extraer_json(respuesta.contenido)
            break
        except ValueError as exc:
            logger.warning("Extracción sin JSON válido (intento {}): {}", intento, exc)
            mensajes += [{"role": "assistant", "content": respuesta.contenido[:2000]},
                         {"role": "user", "content": "El JSON anterior no es válido o quedó cortado. Devuelve solo JSON válido y más corto: máximo 8 chequeos y 3 hechos."}]
    if datos is None:
        return [], [], ["el modelo no devolvió un JSON válido tras reintentar"]
    if usar_cache and not ruta.exists():
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        ruta.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")

    descartados: list[str] = []
    chequeos: list[ChequeoNumerico] = []
    lista = lambda v: v if isinstance(v, list) else []  # noqa: E731  (null o dict donde va una lista)
    for i, bruto in enumerate(lista(datos.get("chequeos"))[:MAX_CHEQUEOS], 1):
        try:
            chequeos.append(ChequeoNumerico.model_validate(bruto))
        except ValidationError as exc:
            descartados.append(f"chequeo {bruto.get('id', i) if isinstance(bruto, dict) else i}: {exc.errors()[0]['msg']}")
    hechos: list[HechoReal] = []
    for i, bruto in enumerate(lista(datos.get("hechos"))[:MAX_HECHOS], 1):
        if isinstance(bruto, str):  # el modelo a veces devuelve solo el enunciado
            bruto = {"id": f"h{i}", "afirmacion": bruto[:300]}
        try:
            hechos.append(HechoReal.model_validate(bruto))
        except ValidationError as exc:
            descartados.append(f"hecho {bruto.get('id', i) if isinstance(bruto, dict) else i}: {exc.errors()[0]['msg']}")
    return chequeos, hechos, descartados
