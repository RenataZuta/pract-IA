"""
Evaluador de la entrevista 1-a-1 con el jefe final (módulo 2).

Toma la transcripción de la respuesta, la pregunta del banco (con su pista de lo que busca el entrevistador) y la
rúbrica de su eje (STAR, técnica o fit) y devuelve el mismo `Feedback` que el group case: el LLM puntúa cada
criterio y el total y los subtotales los calcula el código con los pesos de la rúbrica.

Lee GROQ_API_KEY y GROQ_LLM_MODEL del .env (ver .env.example).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from ai.errores_groq import FALTA_KEY
from ai.evaluator import (
    PALABRAS_POR_MINUTO, EvaluationError, Feedback, _criterios_faltantes, _evaluar_con_reintentos, _format_rubric,
    _load_prompt, _reconciliar, criterios_aplicables,
)

RUBRICA = Path(__file__).parent / "rubrics" / "entrevista.json"
# Tipo de pregunta del banco (archivo en ai/questions/) -> eje de la rúbrica
EJE_DE_TIPO = {
    "behavioral_star": "star", "fit": "fit",
    "tecnica_banca": "tecnica", "tecnica_fmcg": "tecnica", "tecnica_consultoria": "tecnica",
}
# Algunas preguntas no encajan con la rúbrica de su archivo: una debilidad no es STAR ni una pregunta de motivación.
EJE_POR_SUBTEMA = {
    ("fit", "Perfil personal"): "perfil", ("fit", "Criterio y argumentación"): "perfil",
    ("behavioral_star", "Preguntas trampa"): "perfil", ("tecnica_consultoria", "Fit y motivación"): "fit",
}
DURACION_IDEAL_S = (60, 90)
DURACION_ACEPTABLE_S = (45, 120)  # fuera de este rango, "Estructura y duración" no pasa de TOPE_DURACION
CRITERIO_DURACION, TOPE_DURACION = "Estructura y duración", 6


def eje_de(tipo: str, subtema: str | None = None) -> str:
    """Eje de la rúbrica: por tipo de pregunta, salvo los subtemas que no encajan con la de su archivo."""
    if (tipo, subtema) in EJE_POR_SUBTEMA:
        return EJE_POR_SUBTEMA[(tipo, subtema)]
    try:
        return EJE_DE_TIPO[tipo]
    except KeyError:
        raise EvaluationError(f"Tipo de pregunta desconocido: {tipo}") from None


def cargar_rubrica(tipo: str, subtema: str | None = None) -> dict:
    """Rúbrica del eje de la pregunta, con la forma que entiende `criterios_aplicables`."""
    eje = eje_de(tipo, subtema)
    datos = json.loads(RUBRICA.read_text(encoding="utf-8"))["ejes"][eje]
    return {"industry": datos["titulo"], "criterios": datos["criterios"]}


def evaluate_interview_answer(transcript: str, question: dict, tipo: str) -> Feedback:
    """
    Evalúa la respuesta a una pregunta de entrevista.

    Args:
        transcript: lo que dijo el candidato (texto limpio).
        question: pregunta del banco ({pregunta, hint, subtema, ...}).
        tipo: tipo de pregunta ("behavioral_star", "fit", "tecnica_banca"...).

    Raises:
        EvaluationError: texto vacío, falta la key, Groq falla o el JSON sigue siendo inválido tras un reintento.
    """
    if not transcript.strip():
        raise EvaluationError("La respuesta está vacía; no hay nada que evaluar.")
    if not os.getenv("GROQ_API_KEY"):
        raise EvaluationError(FALTA_KEY)
    rubrica = cargar_rubrica(tipo, question.get("subtema"))
    aplicables = criterios_aplicables(rubrica, {})
    messages = [
        {"role": "system", "content": _load_prompt("interview_system.md")},
        {"role": "user", "content": _build_user_prompt(transcript, question, tipo, {**rubrica, "criterios": aplicables})},
    ]
    feedback = _evaluar_con_reintentos(messages, aplicables, [])
    return _aplicar_duracion(feedback, aplicables, transcript)


def _aplicar_duracion(feedback: Feedback, aplicables: list[dict], transcript: str) -> Feedback:
    """La duración la mide el código: si cae fuera de 45-120 s, el criterio de duración no pasa de 6.

    El modelo no es fiable aquí: en una prueba real dio 10/10 a una respuesta de ~30 s diciendo que estaba en rango.
    """
    segundos = segundos_estimados(transcript)
    if DURACION_ACEPTABLE_S[0] <= segundos <= DURACION_ACEPTABLE_S[1]:
        return feedback
    cambio, criterios = False, []
    for c in feedback.criterios:
        if c.nombre == CRITERIO_DURACION and c.puntaje > TOPE_DURACION:
            # El comentario del modelo sobre el tiempo no es fiable (decía "dentro del rango" con 32 s): lo escribe el código.
            motivo = "muy corta" if segundos < DURACION_ACEPTABLE_S[0] else "demasiado larga"
            comentario = (f"Tu respuesta dura unos {segundos} s ({len(transcript.split())} palabras): {motivo}; lo ideal es "
                          f"{DURACION_IDEAL_S[0]}-{DURACION_IDEAL_S[1]} s. Por eso este criterio no pasa de {TOPE_DURACION}/10.")
            c, cambio = c.model_copy(update={"puntaje": TOPE_DURACION, "comentario": comentario}), True
        criterios.append(c)
    if not cambio:
        return feedback
    completo = not _criterios_faltantes(feedback, aplicables)
    return _reconciliar(feedback.model_copy(update={"criterios": criterios}), aplicables, completo=completo)


def segundos_estimados(transcript: str) -> int:
    return round(len(transcript.split()) / PALABRAS_POR_MINUTO * 60)


def _build_user_prompt(transcript: str, question: dict, tipo: str, rubrica: dict) -> str:
    palabras = len(transcript.split())
    return f"""
## Pregunta de la entrevista

**Eje:** {rubrica['industry']} ({tipo})
**Subtema:** {question.get('subtema', '')}

**Pregunta:** {question['pregunta']}

**Lo que busca el entrevistador (y sus red flags):** {question.get('hint', '(sin pista)')}

## Rúbrica de evaluación

{_format_rubric(rubrica, ())}

## Respuesta del candidato

Longitud: {palabras} palabras (~{segundos_estimados(transcript)} s a {PALABRAS_POR_MINUTO} palabras/min; ideal: {DURACION_IDEAL_S[0]}-{DURACION_IDEAL_S[1]} s).

{transcript}

## Tu tarea

Evalúa la respuesta contra la rúbrica y devuelve un JSON con el schema indicado: un objeto en `criterios` por cada criterio de la rúbrica, con su nombre exacto. Responde ÚNICAMENTE con JSON válido.
"""
