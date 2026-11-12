"""
Evaluador del group case.

Toma la transcripción del estudiante, el caso y la rúbrica, y devuelve
feedback estructurado (JSON validado con Pydantic) usando un LLM de Groq.

La rúbrica mezcla criterios técnicos, de habilidades blandas y de aporte propio
(comparación con la respuesta de referencia del caso). El LLM puntúa cada
criterio; el total y los subtotales por tipo los calcula este módulo con los
pesos de la rúbrica, ajustados a los criterios que aplican al caso.

Lee GROQ_API_KEY y GROQ_LLM_MODEL del .env (ver .env.example).
"""
from __future__ import annotations

import json
import os
import re
import unicodedata
from math import floor
from pathlib import Path

from groq import BadRequestError, Groq, GroqError
from loguru import logger
from pydantic import BaseModel, Field, ValidationError, field_validator

from ai.errores_groq import FALTA_KEY, explicar
from ai.rag import formatear, recuperar

PROMPTS_DIR = Path(__file__).parent / "prompts"

# llama-3.3-70b-versatile fue dado de baja en el plan gratuito (2026-08-16).
DEFAULT_LLM_MODEL = "openai/gpt-oss-120b"

RETRY_MESSAGE = (
    "El JSON anterior no es válido, devuelve solo JSON válido que cumpla el schema"
)
PALABRAS_POR_MINUTO = 150
TIEMPO_OBJETIVO_MIN = 3


def _a_entero(valor):
    """Los LLM a veces devuelven 7.5 o 64.5 donde se pide un entero: se redondea (medio hacia arriba)."""
    return floor(valor + 0.5 + 1e-9) if isinstance(valor, float) else valor


# ---------- Schema del feedback ----------
class CriterionScore(BaseModel):
    nombre: str
    puntaje: int = Field(ge=0, le=10)
    comentario: str
    tipo: str | None = None  # "tecnico" | "blando" | "innovacion"; lo completa el sistema
    peso: float | None = None  # fracción de 1, ya ajustada al caso; lo completa el sistema

    @field_validator("puntaje", mode="before")
    @classmethod
    def _redondear(cls, valor):
        return _a_entero(valor)


class ComparativoReferencia(BaseModel):
    coincide: list[str] = []
    aporta: list[str] = []
    le_falto: list[str] = []


class Feedback(BaseModel):
    puntaje_total: int = Field(ge=0, le=100)
    criterios: list[CriterionScore]
    comparativo_referencia: ComparativoReferencia | None = None
    fortaleza_principal: str
    tres_cosas_a_mejorar: list[str]
    red_flags_detectados: list[str] = []
    respuesta_modelo: str
    tiempo_usado_segundos: int | None = None
    puntaje_por_tipo: dict[str, int] = {}  # 0-100 por tipo; lo calcula el sistema
    fuentes_recuperadas: list[str] = []  # fragmentos que el RAG le dio al evaluador; los pone el sistema

    @field_validator("puntaje_total", mode="before")
    @classmethod
    def _redondear(cls, valor):
        return _a_entero(valor)


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
        Feedback validado, con total y subtotales recalculados.

    Raises:
        EvaluationError: si Groq falla o el JSON sigue siendo inválido tras
            un reintento.
    """
    if not transcript.strip():
        raise EvaluationError("La transcripción está vacía; no hay nada que evaluar.")
    if not os.getenv("GROQ_API_KEY"):
        raise EvaluationError(FALTA_KEY)

    aplicables = criterios_aplicables(rubric, case)
    material = _recuperar_material(transcript, case)
    nombres = {c["nombre"] for c in aplicables}
    no_aplican = [c["nombre"] for c in rubric["criterios"] if c["nombre"] not in nombres]
    messages = [
        {"role": "system", "content": _load_prompt("evaluator_system.md")},
        {"role": "user", "content": _build_user_prompt(
            transcript, case, {**rubric, "criterios": aplicables}, no_aplican, material)},
    ]

    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        for intento in (1, 2):
            raw = _complete(client, messages)
            try:
                feedback = Feedback.model_validate_json(raw)
            except ValidationError as exc:
                if intento == 2:
                    raise
                logger.warning("JSON inválido del evaluador, reintento una vez: {}", exc)
                correccion = RETRY_MESSAGE
            else:
                faltan = _criterios_faltantes(feedback, aplicables)
                if not faltan:
                    return _con_fuentes(_reconciliar(feedback, aplicables, completo=True), material)
                if intento == 2:
                    logger.warning("Faltan criterios tras el reintento ({}); se conserva el total del modelo.", faltan)
                    return _con_fuentes(_reconciliar(feedback, aplicables, completo=False), material)
                logger.warning("Faltan criterios en la respuesta del evaluador, reintento una vez: {}", faltan)
                correccion = (
                    f"Faltan estos criterios de la rúbrica: {', '.join(faltan)}. Devuelve el JSON completo con "
                    "un objeto por cada criterio y su nombre exacto."
                )
            if raw:
                messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user", "content": correccion})
    except ValidationError as exc:
        logger.error("El evaluador devolvió JSON inválido dos veces: {}", exc)
        raise EvaluationError("El evaluador devolvió un JSON inválido dos veces.") from exc
    except GroqError as exc:
        logger.error("Error al llamar a Groq: {}", exc)
        raise EvaluationError(explicar(exc)) from exc
    raise EvaluationError("El evaluador no devolvió feedback.")  # inalcanzable; satisface al type checker


def criterios_aplicables(rubric: dict, case: dict) -> list[dict]:
    """
    Criterios de la rúbrica que aplican al caso, con los pesos ajustados.

    Un criterio con `aplica_a` solo cuenta para esos `case_type`, y el caso puede excluir criterios
    con `criterios_no_aplican` (lista de nombres). El peso de los
    que no aplican se reparte entre los demás criterios de su mismo tipo, para no
    cambiar el balance entre técnico, habilidades blandas y aporte propio.
    """
    todos = rubric["criterios"]
    excluidos = set(case.get("criterios_no_aplican", []))  # el caso no pide eso (p. ej. no pide recomendación)
    aplican = [c for c in todos
               if c["nombre"] not in excluidos and (not c.get("aplica_a") or case.get("case_type") in c["aplica_a"])]
    resultado: list[dict] = []
    for tipo in dict.fromkeys(c.get("tipo", "tecnico") for c in todos):
        peso_grupo = sum(c["peso"] for c in todos if c.get("tipo", "tecnico") == tipo)
        grupo = [c for c in aplican if c.get("tipo", "tecnico") == tipo]
        suma = sum(c["peso"] for c in grupo)
        if not grupo or suma <= 0:
            continue
        resultado += [{**c, "tipo": tipo, "peso": c["peso"] * peso_grupo / suma} for c in grupo]
    total = sum(c["peso"] for c in resultado)
    if resultado and abs(total - 1) > 1e-9:  # un grupo entero sin criterios aplicables
        resultado = [{**c, "peso": c["peso"] / total} for c in resultado]
    return resultado


# ---------- Helpers ----------
def _recuperar_material(transcript: str, case: dict) -> list[str]:
    """RAG: fragmentos del corpus parecidos al caso y a la respuesta (RAG_K=0 lo desactiva)."""
    try:
        k = int(os.getenv("RAG_K", "3"))
        if k <= 0:
            return []
        consulta = f"{case['title']} {case['case_type']} {' '.join(case.get('temas_evaluados', []))} {transcript}"
        return formatear(recuperar(consulta, k=k, excluir_caso=case.get("id")))
    except Exception as exc:  # el RAG es un apoyo: si falla, se evalúa igual
        logger.warning("RAG no disponible, se evalúa sin material de apoyo: {}", exc)
        return []


def _con_fuentes(feedback: Feedback, material: list[str]) -> Feedback:
    return feedback.model_copy(update={"fuentes_recuperadas": material})


def _load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def _complete(client: Groq, messages: list[dict]) -> str:
    """Una llamada al LLM en modo JSON; devuelve el texto de la respuesta."""
    modelo = os.getenv("GROQ_LLM_MODEL", DEFAULT_LLM_MODEL)
    extra: dict = {}
    esfuerzo = os.getenv("GROQ_REASONING_EFFORT", "low")
    if modelo.startswith("openai/gpt-oss") and esfuerzo:
        # Menos razonamiento = menos tokens de salida (el plan gratuito permite 8K tokens/min).
        extra["extra_body"] = {"reasoning_effort": esfuerzo}
    try:
        response = client.chat.completions.create(
            model=modelo,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.3,
            **extra,
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


def _norm(texto: str) -> str:
    ascii_ = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", ascii_.lower()).strip()


def _emparejar(nombre: str, aplicables: list[dict]) -> dict | None:
    """Criterio de la rúbrica que corresponde al nombre devuelto por el LLM (tolera tildes y variaciones)."""
    n = _norm(nombre)
    for c in aplicables:
        if _norm(c["nombre"]) == n:
            return c
    parecidos = [c for c in aplicables if n and (n in _norm(c["nombre"]) or _norm(c["nombre"]) in n)]
    return parecidos[0] if len(parecidos) == 1 else None


def _criterios_faltantes(feedback: Feedback, aplicables: list[dict]) -> list[str]:
    presentes = {c["nombre"] for cs in feedback.criterios if (c := _emparejar(cs.nombre, aplicables))}
    return [c["nombre"] for c in aplicables if c["nombre"] not in presentes]


def _promedio(criterios: list[CriterionScore]) -> int:
    """Promedio ponderado de puntajes 0-10, en escala 0-100."""
    peso = sum(c.peso or 0 for c in criterios)
    if peso <= 0:
        return 0
    # Medio hacia arriba (72.5 -> 73); round() de Python redondea al par.
    puntaje = floor(sum((c.peso or 0) * c.puntaje for c in criterios) / peso * 10 + 0.5 + 1e-9)
    return max(0, min(100, puntaje))


def _reconciliar(feedback: Feedback, aplicables: list[dict], completo: bool) -> Feedback:
    """Nombres, tipo y peso salen de la rúbrica; si están todos los criterios, el total lo calcula el sistema."""
    por_nombre: dict[str, CriterionScore] = {}
    for cs in feedback.criterios:
        c = _emparejar(cs.nombre, aplicables)
        if c is None or c["nombre"] in por_nombre:
            logger.warning("Criterio ignorado (no está en la rúbrica o está repetido): {}", cs.nombre)
            continue
        por_nombre[c["nombre"]] = cs.model_copy(update={"nombre": c["nombre"], "tipo": c["tipo"], "peso": c["peso"]})
    ordenados = [por_nombre[c["nombre"]] for c in aplicables if c["nombre"] in por_nombre]
    if not ordenados:
        return feedback
    cambios: dict = {"criterios": ordenados}
    if completo:
        cambios["puntaje_total"] = _promedio(ordenados)
        cambios["puntaje_por_tipo"] = {
            tipo: _promedio([c for c in ordenados if c.tipo == tipo])
            for tipo in dict.fromkeys(c.tipo for c in ordenados)
        }
    return feedback.model_copy(update=cambios)


def _build_user_prompt(transcript: str, case: dict, rubric: dict, no_aplican: list[str] | tuple = (),
                       material: list[str] | tuple = ()) -> str:
    palabras = len(transcript.split())
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
## Rúbrica de evaluación (pesos ya ajustados a este caso)

{_format_rubric(rubric, no_aplican)}

{_format_reference(case)}{_format_material(material)}## Transcripción de la respuesta del candidato

Longitud: {palabras} palabras (~{palabras / PALABRAS_POR_MINUTO:.1f} min a {PALABRAS_POR_MINUTO} palabras/min; objetivo: {TIEMPO_OBJETIVO_MIN} min).

{transcript}

## Tu tarea

Evalúa la respuesta del candidato contra la rúbrica y devuelve un JSON
con el schema Feedback. Sé riguroso pero constructivo: el candidato es
un estudiante de 10.º ciclo postulando a su primera práctica. Incluye un objeto
en `criterios` por cada criterio de la rúbrica, con su nombre exacto, y el
`comparativo_referencia`.

Responde ÚNICAMENTE con JSON válido que cumpla el schema Feedback, sin texto adicional antes o después.
"""


def _format_rubric(rubric: dict, no_aplican: list[str] | tuple) -> str:
    """Rúbrica compacta para el prompt: pesos en %, sin metadatos internos."""
    data = {
        "industry": rubric.get("industry"),
        "criterios": [
            {
                "nombre": c["nombre"],
                "tipo": c.get("tipo", "tecnico"),
                "peso_pct": round(c["peso"] * 100, 1),
                "descripcion": c["descripcion"],
                # los campos vacíos no se envían: cada token cuenta (el plan gratuito da 8K por minuto)
                **{k: c[k] for k in ("ejemplos_alto", "ejemplos_bajo") if c.get(k)},
            }
            for c in rubric["criterios"]
        ],
    }
    texto = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    if no_aplican:
        texto += "\n\nNo aplican a este caso (no los evalúes): " + ", ".join(no_aplican) + "."
    return texto


def _format_material(material: list[str] | tuple) -> str:
    """Fragmentos recuperados por el RAG (preguntas reales de entrevistadores y casos similares)."""
    if not material:
        return ""
    return (
        "## Material de apoyo recuperado (RAG)\n\n"
        "Fragmentos del corpus de PractIA parecidos a este caso y a la respuesta (criterios de entrevistadores reales y casos "
        "similares). Úsalos para contrastar y calibrar; no los atribuyas al candidato.\n\n"
        + "\n".join(f"- {m}" for m in material) + "\n\n"
    )


def _format_exhibits(case: dict) -> str:
    """Anexos del caso, para poder verificar si el candidato usó bien los números."""
    exhibits = case.get("exhibits") or []
    if not exhibits:
        return ""
    blocks = [f"### Anexo {i}: {e['title']}\n{e['content']}" for i, e in enumerate(exhibits, 1)]
    return "## Anexos del caso\n\n" + "\n\n".join(blocks) + "\n\n"


def _format_reference(case: dict) -> str:
    """Respuesta de referencia (preparada con Claude) y temas del caso; solo para comparar y calibrar."""
    temas = case.get("temas_evaluados") or []
    referencia = case.get("respuesta_referencia") or case.get("pista_respuesta_modelo")
    if not temas and not referencia:
        return ""
    lines = ["## Respuesta de referencia del caso (preparada con Claude; úsala solo para comparar y calibrar, no es del candidato)"]
    if temas:
        lines.append("**Temas evaluados:** " + "; ".join(temas))
    if referencia:
        lines.append(referencia)
    return "\n\n".join(lines) + "\n\n"
