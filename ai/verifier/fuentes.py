"""
Guardarraíles de las fuentes: "sin cita verificada no hay veredicto".

La búsqueda de Groq corre en sus servidores y devuelve en `executed_tools` todo lo que
consultó (URLs de resultados y texto de las páginas abiertas). Aquí se reconstruye ese
registro y se contrasta con lo que el modelo dice haber leído:

- una fuente solo cuenta si su URL aparece entre los resultados o páginas del registro;
- su cita solo está "verificada" si se encuentra en el texto de esa página abierta;
- un veredicto "confirmado" o "contradicho" sin ninguna cita verificada se degrada a
  "no_verificable". El modelo no puede saltarse esto con el prompt: lo impone el código.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit, urlunsplit

from ai.verifier.citas import cita_en_texto
from ai.verifier.modelos import Fuente, RespuestaHecho, VeredictoHecho

MAX_PALABRAS_CITA = 40


def normalizar_url(url: str) -> str:
    partes = urlsplit(url.strip())
    return urlunsplit((partes.scheme.lower(), partes.netloc.lower(), partes.path.rstrip("/"), partes.query, ""))


@dataclass
class Registro:
    """Lo que la búsqueda consultó de verdad en una llamada."""

    consultas: list[str] = field(default_factory=list)
    resultados: dict[str, str] = field(default_factory=dict)  # url -> título (resultados de búsqueda)
    paginas: dict[str, str] = field(default_factory=dict)  # url -> texto (páginas abiertas)

    def conoce(self, url: str) -> bool:
        u = normalizar_url(url)
        return u in {normalizar_url(x) for x in (*self.resultados, *self.paginas)}

    def texto_de(self, url: str) -> str | None:
        u = normalizar_url(url)
        return next((t for p, t in self.paginas.items() if normalizar_url(p) == u), None)

    def titulo_de(self, url: str) -> str:
        u = normalizar_url(url)
        return next((t for p, t in self.resultados.items() if normalizar_url(p) == u), "")


def registro_desde(mensaje) -> Registro:
    """Reconstruye el registro desde `message.executed_tools` de la respuesta de Groq."""
    registro = Registro()
    extra = getattr(mensaje, "model_extra", None) or {}
    for herramienta in extra.get("executed_tools") or []:
        tipo = str(herramienta.get("type") or herramienta.get("name") or "")
        try:
            argumentos = json.loads(herramienta.get("arguments") or "{}")
        except (TypeError, ValueError):
            argumentos = {}
        resultados = (herramienta.get("search_results") or {}).get("results") or []
        if tipo.endswith("search") or tipo == "browser_search":
            if argumentos.get("query"):
                registro.consultas.append(str(argumentos["query"]))
            for r in resultados:
                if r.get("url"):
                    registro.resultados[r["url"]] = r.get("title") or ""
        else:  # browser.open / browser.find: texto de una página
            for r in resultados:
                url = r.get("url")
                if url:
                    texto = r.get("content") or herramienta.get("output") or ""
                    registro.paginas[url] = registro.paginas.get(url, "") + "\n" + texto
                    registro.resultados.setdefault(url, r.get("title") or "")
    return registro


def limpiar_cita(cita: str) -> str:
    """Deja solo la cita: si el modelo la fusionó con un comentario («cita» | explicación), toma lo que va entre « »."""
    m = re.search(r"[«“\"](.+?)[»”\"]", cita, re.S)
    return (m.group(1) if m else cita).strip()


def aplicar_guardarrailes(
    respuesta: RespuestaHecho, registro: Registro, *, id: str, afirmacion: str, tipo: str, fecha: str
) -> VeredictoHecho:
    """Convierte la respuesta del modelo en un veredicto que el código puede sostener."""
    fuentes: list[Fuente] = []
    ignoradas = 0
    for f in respuesta.fuentes:
        url, cita = str(f.get("url") or ""), limpiar_cita(str(f.get("cita") or ""))
        if not url or not registro.conoce(url):
            ignoradas += 1  # URL que el agente no consultó: se descarta
            continue
        texto = registro.texto_de(url)
        verificada = bool(texto) and 0 < len(cita.split()) <= MAX_PALABRAS_CITA and cita_en_texto(cita, texto or "")
        fuentes.append(Fuente(titulo=str(f.get("titulo") or registro.titulo_de(url) or url), url=url,
                              cita=cita, cita_verificada=verificada))

    veredicto, nota = respuesta.veredicto, ""
    if ignoradas:
        nota = f"{ignoradas} fuente(s) citadas por el modelo no figuran en lo que consultó y se descartaron. "
    if veredicto != "no_verificable" and not any(f.cita_verificada for f in fuentes):
        veredicto = "no_verificable"
        nota += "El modelo propuso un veredicto, pero ninguna cita textual se encontró en una página abierta."
    return VeredictoHecho(
        id=id, afirmacion=afirmacion, tipo=tipo, veredicto=veredicto,
        resumen=respuesta.resumen, correccion_sugerida=respuesta.correccion_sugerida if veredicto == "contradicho" else None,
        fuentes=fuentes, busquedas=registro.consultas, paginas_abiertas=list(registro.paginas),
        consultado=fecha, nota=nota.strip(),
    )


_VALLA = re.compile(r"^```(?:json)?\s*|\s*```$", re.I)


def extraer_json(texto: str) -> dict:
    """Saca el objeto JSON de la respuesta aunque venga con ```json o con texto alrededor."""
    t = _VALLA.sub("", (texto or "").strip())
    try:
        objeto = json.loads(t)
    except ValueError:
        inicio, fin = t.find("{"), t.rfind("}")
        if inicio == -1 or fin <= inicio:
            raise ValueError("la respuesta no contiene un objeto JSON") from None
        objeto = json.loads(t[inicio : fin + 1])
    if not isinstance(objeto, dict):  # p. ej. una lista suelta
        raise ValueError("la respuesta es JSON pero no un objeto")
    return objeto
