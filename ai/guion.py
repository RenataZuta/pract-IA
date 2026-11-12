"""
Guion final para practicar.

Combina la respuesta del estudiante con el contraste del evaluador (lo que
coincidió con la referencia, lo que aportó, lo que le faltó y sus puntos a mejorar)
en un guion hablado de ~3 minutos, dividido en bloques con tiempo. Es una segunda
llamada al LLM, aparte de la evaluación, para no gastar más tokens en el flujo
principal (el plan gratuito de Groq permite 8K tokens/min).
"""
from __future__ import annotations

import os

from groq import Groq, GroqError
from loguru import logger
from pydantic import BaseModel, ValidationError, field_validator

from ai.errores_groq import FALTA_KEY, explicar
from ai.evaluator import RETRY_MESSAGE, Feedback, _a_entero, _complete, _format_exhibits, _load_prompt

PALABRAS_POR_MINUTO = 150
PALABRAS_OBJETIVO = 430  # ~3 min hablando
PALABRAS_MINIMO = 360  # menos de ~2.5 min: queda corto para la respuesta de 3 min
PALABRAS_MAXIMO = 470  # ~3:08 min; por encima se pide recortar


class GuionError(RuntimeError):
    """No se pudo generar el guion (Groq limitando, key inválida, JSON roto)."""


class BloqueGuion(BaseModel):
    nombre: str
    segundos: int
    texto: str

    @field_validator("segundos", mode="before")
    @classmethod
    def _redondear(cls, valor):
        return _a_entero(valor)


class GuionFinal(BaseModel):
    bloques: list[BloqueGuion]
    cambios: list[str] = []
    consejos: list[str] = []

    @property
    def palabras(self) -> int:
        return sum(len(b.texto.split()) for b in self.bloques)

    @property
    def segundos(self) -> int:
        return sum(b.segundos for b in self.bloques)


def generar_guion(transcript: str, case: dict, feedback: Feedback) -> GuionFinal:
    """
    Guion final a partir de la respuesta del estudiante y el feedback de la evaluación.

    Raises:
        GuionError: si Groq falla o el JSON sigue siendo inválido tras un reintento.
    """
    if not transcript.strip():
        raise GuionError("No hay respuesta para convertir en guion.")
    if not os.getenv("GROQ_API_KEY"):
        raise GuionError(FALTA_KEY)

    messages = [
        {"role": "system", "content": _load_prompt("guion_system.md")},
        {"role": "user", "content": _build_user_prompt(transcript, case, feedback)},
    ]
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        for intento in (1, 2):
            raw = _complete(client, messages)
            try:
                guion = GuionFinal.model_validate_json(raw)
                if not guion.bloques:
                    raise ValueError("sin bloques")
            except (ValidationError, ValueError) as exc:
                if intento == 2:
                    raise GuionError("El guion devolvió un JSON inválido dos veces.") from exc
                logger.warning("JSON inválido del guion, reintento una vez: {}", exc)
                correccion = RETRY_MESSAGE
            else:
                fuera = guion.palabras > PALABRAS_MAXIMO or guion.palabras < PALABRAS_MINIMO
                if not fuera or intento == 2:
                    if fuera:
                        logger.warning("El guion quedó de {} palabras (objetivo ~{}).", guion.palabras, PALABRAS_OBJETIVO)
                    return _con_tiempos_reales(guion)
                logger.warning("Guion de {} palabras, reintento una vez para ajustarlo.", guion.palabras)
                if guion.palabras > PALABRAS_MAXIMO:
                    correccion = (f"El guion tiene {guion.palabras} palabras y no cabe en 3 minutos. Recórtalo a unas "
                                  f"{PALABRAS_OBJETIVO} palabras manteniendo los bloques y devuelve el JSON completo.")
                else:
                    correccion = (f"El guion tiene solo {guion.palabras} palabras y se queda corto para 3 minutos. Amplíalo a unas "
                                  f"{PALABRAS_OBJETIVO} palabras con contenido útil (cifras de los anexos, riesgos, supuestos, "
                                  "ideas propias del estudiante), sin relleno, y devuelve el JSON completo.")
            if raw:
                messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user", "content": correccion})
    except GroqError as exc:
        logger.error("Error al llamar a Groq para el guion: {}", exc)
        raise GuionError(explicar(exc)) from exc
    raise GuionError("No se pudo generar el guion.")  # inalcanzable


def _con_tiempos_reales(guion: GuionFinal) -> GuionFinal:
    """El tiempo de cada bloque sale de sus palabras (150/min), no de lo que diga el modelo."""
    bloques = [
        b.model_copy(update={"segundos": max(5, round(len(b.texto.split()) / PALABRAS_POR_MINUTO * 60))})
        for b in guion.bloques
    ]
    return guion.model_copy(update={"bloques": bloques})


def _build_user_prompt(transcript: str, case: dict, feedback: Feedback) -> str:
    referencia = case.get("respuesta_referencia") or case.get("pista_respuesta_modelo", "")
    cmp = feedback.comparativo_referencia
    criterios = "\n".join(f"- {c.nombre}: {c.puntaje}/10 — {c.comentario}" for c in feedback.criterios)
    por_tipo = ", ".join(f"{t} {p}/100" for t, p in feedback.puntaje_por_tipo.items())
    lista = lambda items: "; ".join(items) if items else "(nada)"  # noqa: E731
    return f"""
## Caso

**Empresa:** {case['company']} · **Tipo:** {case['case_type']}

**Contexto:**
{case['context']}

**Pregunta:**
{case['prompt']}

{_format_exhibits(case)}## Respuesta de referencia (guía; no la copies)

{referencia}

## Respuesta del estudiante (transcripción)

{transcript}

## Contraste de la evaluación

Puntaje total: {feedback.puntaje_total}/100 ({por_tipo or 'sin desglose'})

Criterios:
{criterios}

- Coincidió con la referencia en: {lista(cmp.coincide if cmp else [])}
- Aportó por su cuenta (conserva y refuerza): {lista(cmp.aporta if cmp else [])}
- Le faltó respecto a la referencia: {lista(cmp.le_falto if cmp else [])}
- Cosas a mejorar: {lista(feedback.tres_cosas_a_mejorar)}
- Red flags: {lista(feedback.red_flags_detectados)}

## Tu tarea

Escribe el guion final para practicar, en bloques con tiempo, de entre {PALABRAS_MINIMO + 40} y {PALABRAS_OBJETIVO + 20} palabras en total (cuéntalas).

Responde ÚNICAMENTE con JSON válido que cumpla el formato indicado, sin texto adicional antes o después.
"""


def hhmmss(segundos: int) -> str:
    return f"{segundos // 60}:{segundos % 60:02d}"

