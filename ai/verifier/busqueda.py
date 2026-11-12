"""Paso 3: un LLM con búsqueda web verifica un hecho; los guardarraíles deciden si el veredicto se sostiene."""
from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

from loguru import logger
from pydantic import ValidationError

from ai.verifier.fuentes import Registro, aplicar_guardarrailes, extraer_json, registro_desde
from ai.verifier.llm import LlmVerificador, SolicitudMuyGrande, VerificadorError
from ai.verifier.modelos import HechoReal, RespuestaHecho, VeredictoHecho

PROMPTS = Path(__file__).resolve().parent.parent / "prompts"
PROMPT_INVESTIGAR, PROMPT_VEREDICTO = PROMPTS / "verificador_hechos.md", PROMPTS / "verificador_veredicto.md"
CACHE_DIR = Path(__file__).resolve().parent.parent / "audits" / ".cache"
HERRAMIENTAS = [{"type": "browser_search"}]  # búsqueda y lectura web integradas de Groq (misma GROQ_API_KEY)


def _clave_cache(hecho: HechoReal, modelo: str) -> Path:
    h = hashlib.sha256(f"{modelo}|{hecho.afirmacion}".encode()).hexdigest()[:20]
    return CACHE_DIR / f"{h}.json"


def verificar_hecho(hecho: HechoReal, contexto: str, llm: LlmVerificador, *, usar_cache: bool = True) -> VeredictoHecho:
    """Busca, lee y emite un veredicto con fuentes. Si algo falla, devuelve no_verificable con el motivo."""
    ruta = _clave_cache(hecho, llm.modelo)
    if usar_cache and ruta.exists():
        logger.info("Hecho {} desde caché", hecho.id)
        return VeredictoHecho.model_validate_json(ruta.read_text(encoding="utf-8"))

    hoy = date.today().isoformat()
    base = dict(id=hecho.id, afirmacion=hecho.afirmacion, tipo=hecho.tipo, fecha=hoy)
    try:
        # Paso 1: investiga con la búsqueda de Groq y escribe un informe en prosa. No se le pide JSON aquí:
        # con tool_choice="required" el modelo intenta devolver su JSON como si fuera una herramienta y Groq lo rechaza.
        investigar = [
            {"role": "system", "content": PROMPT_INVESTIGAR.read_text(encoding="utf-8")},
            {"role": "user", "content": f"Hoy es {hoy}. Contexto: {contexto}\n\nAfirmación a verificar: {hecho.afirmacion}\n"
                                        f"(Cita del caso: «{hecho.cita_caso}»)"},
        ]
        respuesta = llm.completar(investigar, tools=HERRAMIENTAS, max_tokens=3500, estimado=7000)
        registro: Registro = registro_desde(respuesta.mensaje)
        if not registro.paginas or not respuesta.contenido.strip():
            # Sin una página abierta no hay cita que verificar: no se gasta una segunda llamada.
            veredicto = _sin_veredicto(base, "el agente no abrió ninguna página, así que no hay fuente que verificar", registro)
        else:
            # Paso 2: estructura el informe en JSON (sin herramientas). Los guardarraíles lo contrastan con el registro.
            estructurar = [
                {"role": "system", "content": PROMPT_VEREDICTO.read_text(encoding="utf-8")},
                {"role": "user", "content": f"Afirmación: {hecho.afirmacion}\n\nInforme del investigador:\n"
                                            f"{respuesta.contenido[:5000]}\n\nPáginas que abrió: {', '.join(registro.paginas)}"},
            ]
            parsed = _parsear(llm.completar(estructurar, json_mode=True, max_tokens=1500, estimado=2500).contenido)
            if parsed is None:
                estructurar.append({"role": "user", "content": "Devuelve solo el JSON del schema pedido, sin texto adicional."})
                parsed = _parsear(llm.completar(estructurar, json_mode=True, max_tokens=1500, estimado=2500).contenido)
            if parsed is None:
                raise VerificadorError("el modelo no devolvió un JSON válido")
            veredicto = aplicar_guardarrailes(parsed, registro, **base)
    except SolicitudMuyGrande:
        veredicto = _sin_veredicto(base, "la página era demasiado grande para el límite de tokens del plan gratuito")
    except VerificadorError as exc:
        veredicto = _sin_veredicto(base, f"no se pudo verificar: {exc}")
    else:
        if usar_cache:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            ruta.write_text(veredicto.model_dump_json(indent=2), encoding="utf-8")
    logger.info("Hecho {}: {} ({} fuentes)", hecho.id, veredicto.veredicto, len(veredicto.fuentes))
    return veredicto


def _parsear(texto: str) -> RespuestaHecho | None:
    try:
        return RespuestaHecho.model_validate(extraer_json(texto))
    except (ValueError, ValidationError):
        return None


def _sin_veredicto(base: dict, motivo: str, registro: Registro | None = None) -> VeredictoHecho:
    return VeredictoHecho(veredicto="no_verificable", resumen="", consultado=base["fecha"], nota=motivo,
                          busquedas=registro.consultas if registro else [],
                          **{k: v for k, v in base.items() if k != "fecha"})
