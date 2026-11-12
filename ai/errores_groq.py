"""Traduce los errores de Groq a mensajes que el estudiante entiende (y que dicen qué hacer)."""
from __future__ import annotations

import re

from groq import APIConnectionError, APIStatusError, APITimeoutError, AuthenticationError, RateLimitError

FALTA_KEY = "Falta GROQ_API_KEY: ponla en el archivo .env (local) o en Settings → Secrets (Streamlit Cloud)."


def _segundos(exc: RateLimitError) -> int | None:
    cabecera = getattr(getattr(exc, "response", None), "headers", {}) or {}
    try:
        if cabecera.get("retry-after"):
            return max(1, round(float(cabecera["retry-after"])))
    except ValueError:
        pass
    m = re.search(r"try again in (\d+(?:\.\d+)?)\s*(ms|s|m)\b", str(exc))
    if not m:
        return None
    valor = float(m.group(1))
    return max(1, round(valor / 1000 if m.group(2) == "ms" else valor * 60 if m.group(2) == "m" else valor))


def explicar(exc: Exception) -> str:
    """Mensaje claro para un error de Groq; el detalle técnico se queda en el log."""
    texto = str(exc).lower()
    if isinstance(exc, RateLimitError):
        if "per day" in texto or "tpd" in texto:
            return ("Se agotó el cupo diario de Groq (plan gratuito: 200K tokens al día). Se repone en unas horas; "
                    "puedes ver tu uso en console.groq.com.")
        if "too large" in texto:
            return "La petición es demasiado grande para el límite por minuto del plan gratuito (8K tokens). Prueba con una respuesta más corta."
        espera = _segundos(exc)
        cuando = f"unos {espera} segundos" if espera else "un minuto"
        return f"Groq está limitando las llamadas del plan gratuito (8K tokens por minuto). Espera {cuando} y vuelve a intentar."
    if isinstance(exc, AuthenticationError):
        return "La GROQ_API_KEY no es válida o fue revocada. Revísala en el .env (local) o en Secrets (Streamlit Cloud)."
    if isinstance(exc, APIStatusError):
        if exc.status_code == 413:
            return "La petición es demasiado grande para el plan gratuito de Groq. Prueba con una respuesta más corta."
        if exc.status_code == 404 or "decommissioned" in texto:
            return "El modelo configurado ya no está disponible en Groq. Revisa GROQ_LLM_MODEL en el .env."
        if exc.status_code >= 500:
            return "Groq tuvo un problema temporal. Intenta de nuevo en un momento."
    if isinstance(exc, (APIConnectionError, APITimeoutError)):
        return "No hay conexión con Groq. Revisa tu internet y vuelve a intentar."
    return f"Error al llamar a Groq: {exc}"
