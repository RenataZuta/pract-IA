"""
Evaluador del group case.

Toma la transcripción del estudiante, el caso y la rúbrica, y devuelve
feedback estructurado (JSON validado con Pydantic).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

from loguru import logger
from pydantic import BaseModel, Field

PROMPTS_DIR = Path(__file__).parent / "prompts"


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


# ---------- API pública ----------
def evaluate_response(
    transcript: str,
    case: dict,
    rubric: dict,
    provider: Literal["openai", "anthropic"] = "openai",
) -> Feedback:
    """
    Evalúa la respuesta del estudiante contra la rúbrica.

    Args:
        transcript: lo que dijo el estudiante (texto limpio).
        case: dict del caso (industry, company, context, prompt, exhibits).
        rubric: dict de la rúbrica (criterios con pesos y descripciones).
        provider: "openai" o "anthropic".

    Returns:
        Feedback validado.
    """
    system_prompt = _load_prompt("evaluator_system.md")
    user_prompt = _build_user_prompt(transcript, case, rubric)

    if provider == "openai":
        return _evaluate_openai(system_prompt, user_prompt)
    elif provider == "anthropic":
        return _evaluate_anthropic(system_prompt, user_prompt)
    else:
        raise ValueError(f"Provider desconocido: {provider}")


# ---------- Helpers ----------
def _load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


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

## Rúbrica de evaluación

{json.dumps(rubric, ensure_ascii=False, indent=2)}

## Transcripción de la respuesta del candidato

{transcript}

## Tu tarea

Evalúa la respuesta del candidato contra la rúbrica y devuelve un JSON
con el schema Feedback. Sé riguroso pero constructivo: el candidato es
un estudiante de 10.º ciclo postulando a su primera práctica.
"""


def _evaluate_openai(system: str, user: str) -> Feedback:
    """Llama GPT-4o-mini con structured output."""
    # TODO Claude Code:
    # from openai import OpenAI
    # client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    # response = client.beta.chat.completions.parse(
    #     model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    #     messages=[
    #         {"role": "system", "content": system},
    #         {"role": "user", "content": user},
    #     ],
    #     response_format=Feedback,
    # )
    # return response.choices[0].message.parsed
    logger.warning("Evaluador OpenAI es stub — conectar.")
    return _stub_feedback()


def _evaluate_anthropic(system: str, user: str) -> Feedback:
    """Llama Claude Haiku con tool-use para forzar JSON."""
    # TODO Claude Code: usar anthropic.Anthropic().messages.create con
    # tool_choice para forzar estructura Feedback.
    logger.warning("Evaluador Anthropic es stub — conectar.")
    return _stub_feedback()


def _stub_feedback() -> Feedback:
    return Feedback(
        puntaje_total=0,
        criterios=[CriterionScore(nombre="stub", puntaje=0, comentario="pendiente")],
        fortaleza_principal="[STUB]",
        tres_cosas_a_mejorar=["[STUB]"],
        respuesta_modelo="[STUB]",
    )
