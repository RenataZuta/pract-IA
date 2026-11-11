"""
Evaluador del group case.

Toma la transcripción del estudiante, el caso y la rúbrica, y devuelve
feedback estructurado (JSON validado con Pydantic) usando un LLM de Groq.

Lee GROQ_API_KEY y GROQ_LLM_MODEL del .env (ver .env.example).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from groq import BadRequestError, Groq, GroqError
from loguru import logger
from pydantic import BaseModel, Field, ValidationError

PROMPTS_DIR = Path(__file__).parent / "prompts"

# llama-3.3-70b-versatile fue dado de baja en el plan gratuito (2026-08-16).
DEFAULT_LLM_MODEL = "openai/gpt-oss-120b"

RETRY_MESSAGE = (
    "El JSON anterior no es válido, devuelve solo JSON válido que cumpla el schema"
)


# ---------- Schema del feedback ----------
class CriterionScore(BaseModel):
    nombre: str
    puntaje: int = Field(ge=0, le=10)
    comentario: str


class Feedback(BaseModel):
    puntaje_total: int = Field(ge=0, le=100)
    criterios: list[CriterionScore]
    fortaleza_principal: str
    tres_cosas_a_mejorar: list[str]
    red_flags_detectados: list[str] = []
    respuesta_modelo: str
    tiempo_usado_segundos: int | None = None


class EvaluationError(RuntimeError):
    """No se pudo obtener un feedback válido (Groq caído, key inválida, JSON roto)."""


# ---------- API pública ----------
def evaluate_response(transcript: str, case: dict, rubric: dict) -> Feedback:
    """
    Evalúa la respuesta del estudiante contra la rúbrica.

    Args:
        transcript: lo que dijo el estudiante (texto limpio).
        case: dict del caso (industry, company, context, prompt, exhibits).
        rubric: dict de la rúbrica (criterios con pesos y descripciones).

    Returns:
        Feedback validado.

    Raises:
        EvaluationError: si Groq falla o el JSON sigue siendo inválido tras
            un reintento.
    """
    if not transcript.strip():
        raise EvaluationError("La transcripción está vacía; no hay nada que evaluar.")
    if not os.getenv("GROQ_API_KEY"):
        raise EvaluationError("Falta GROQ_API_KEY en el .env.")

    messages = [
        {"role": "system", "content": _load_prompt("evaluator_system.md")},
        {"role": "user", "content": _build_user_prompt(transcript, case, rubric)},
    ]

    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        raw = _complete(client, messages)
        try:
            return Feedback.model_validate_json(raw)
        except ValidationError as exc:
            logger.warning("JSON inválido del evaluador, reintento una vez: {}", exc)

        if raw:
            messages.append({"role": "assistant", "content": raw})
        messages.append({"role": "user", "content": RETRY_MESSAGE})
        return Feedback.model_validate_json(_complete(client, messages))
    except ValidationError as exc:
        logger.error("El evaluador devolvió JSON inválido dos veces: {}", exc)
        raise EvaluationError("El evaluador devolvió un JSON inválido dos veces.") from exc
    except GroqError as exc:
        logger.error("Error al llamar a Groq: {}", exc)
        raise EvaluationError(f"Error al llamar a Groq: {exc}") from exc


# ---------- Helpers ----------
def _load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def _complete(client: Groq, messages: list[dict]) -> str:
    """Una llamada al LLM en modo JSON; devuelve el texto de la respuesta."""
    try:
        response = client.chat.completions.create(
            model=os.getenv("GROQ_LLM_MODEL", DEFAULT_LLM_MODEL),
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.3,
        )
    except BadRequestError as exc:
        # El modo JSON de Groq responde 400 si el modelo no logra producir JSON
        # válido; eso se reintenta. Cualquier otro 400 (modelo dado de baja,
        # parámetros) se propaga para que se vea el motivo real.
        body = exc.body if isinstance(exc.body, dict) else {}
        error = body.get("error", body)
        if error.get("code") != "json_validate_failed":
            raise
        return error.get("failed_generation") or ""
    return response.choices[0].message.content or ""


def _build_user_prompt(transcript: str, case: dict, rubric: dict) -> str:
    return f"""
## Caso presentado al candidato

**Empresa:** {case['company']}
**Industria:** {case['industry']}
**Tipo:** {case['case_type']}

**Contexto:**
{case['context']}

**Pregunta:**
{case['prompt']}

{_format_exhibits(case)}
## Rúbrica de evaluación

{json.dumps(rubric, ensure_ascii=False, indent=2)}

{_format_reference(case)}
## Transcripción de la respuesta del candidato

{transcript}

## Tu tarea

Evalúa la respuesta del candidato contra la rúbrica y devuelve un JSON
con el schema Feedback. Sé riguroso pero constructivo: el candidato es
un estudiante de 10.º ciclo postulando a su primera práctica.

Responde ÚNICAMENTE con JSON válido que cumpla el schema Feedback, sin texto adicional antes o después.
"""


def _format_exhibits(case: dict) -> str:
    """Anexos del caso, para poder verificar si el candidato usó bien los números."""
    exhibits = case.get("exhibits") or []
    if not exhibits:
        return ""
    blocks = [f"### Anexo {i}: {e['title']}\n{e['content']}" for i, e in enumerate(exhibits, 1)]
    return "## Anexos del caso\n\n" + "\n\n".join(blocks) + "\n\n"


def _format_reference(case: dict) -> str:
    """Pistas internas del caso; solo para calibrar la evaluación."""
    temas = case.get("temas_evaluados") or []
    pista = case.get("pista_respuesta_modelo")
    if not temas and not pista:
        return ""
    lines = ["## Referencia interna del caso (úsala para calibrar, no la cites como del candidato)"]
    if temas:
        lines.append("**Temas evaluados:** " + "; ".join(temas))
    if pista:
        lines.append(f"**Pista de respuesta modelo:** {pista}")
    return "\n\n".join(lines) + "\n\n"
