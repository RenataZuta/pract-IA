"""
Llamadas a Groq para el verificador: ritmo de tokens, reintentos y errores claros.

El plan gratuito permite 8K tokens por minuto y una verificación con búsqueda gasta ~7K,
así que este módulo espera lo necesario entre llamadas en vez de fallar con 429.
"""
from __future__ import annotations

import os
import re
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable

from groq import APIConnectionError, APIStatusError, APITimeoutError, BadRequestError, Groq, RateLimitError
from loguru import logger

DEFAULT_LLM_MODEL = "openai/gpt-oss-120b"  # el único del plan gratuito con búsqueda web integrada
TPM_GRATIS = 8000
MAX_REINTENTOS = 3


class VerificadorError(RuntimeError):
    """No se pudo completar una llamada (key faltante, límite, modelo sin búsqueda, etc.)."""


class SolicitudMuyGrande(VerificadorError):
    """La petición no cabe en el límite de tokens por minuto del plan (p. ej. una página enorme)."""


@dataclass
class Respuesta:
    contenido: str
    mensaje: Any  # el mensaje crudo: ahí viene `executed_tools` con lo que buscó el modelo
    tokens: int


def _segundos_de_espera(exc: RateLimitError) -> float:
    cabecera = getattr(getattr(exc, "response", None), "headers", {}) or {}
    if cabecera.get("retry-after"):
        try:
            return min(float(cabecera["retry-after"]), 90.0)
        except ValueError:
            pass
    m = re.search(r"try again in (\d+(?:\.\d+)?)\s*(ms|s|m)\b", str(exc))
    if m:
        valor = float(m.group(1))
        return min(valor / 1000 if m.group(2) == "ms" else valor * 60 if m.group(2) == "m" else valor, 90.0)
    return 20.0


class LlmVerificador:
    """Cliente de Groq con ritmo de tokens por minuto. `cliente` y `dormir` se inyectan en las pruebas."""

    def __init__(self, cliente: Any = None, modelo: str | None = None, tpm: int = TPM_GRATIS,
                 dormir: Callable[[float], None] = time.sleep, reloj: Callable[[], float] = time.monotonic):
        self._cliente = cliente
        self.modelo = modelo or os.getenv("GROQ_LLM_MODEL", DEFAULT_LLM_MODEL)
        self.tpm, self._dormir, self._reloj = tpm, dormir, reloj
        self._uso: deque[tuple[float, int]] = deque()  # (cuándo, tokens) en la última ventana de 60 s

    @property
    def cliente(self):
        if self._cliente is None:
            if not os.getenv("GROQ_API_KEY"):
                raise VerificadorError("Falta GROQ_API_KEY en el entorno (.env). Ver .env.example.")
            self._cliente = Groq(api_key=os.getenv("GROQ_API_KEY"))
        return self._cliente

    def _esperar(self, estimado: int) -> None:
        """Duerme lo justo para que esta llamada no pase de `tpm` tokens en 60 s."""
        ahora = self._reloj()
        while self._uso and ahora - self._uso[0][0] >= 60:
            self._uso.popleft()
        usado = sum(t for _, t in self._uso)
        if usado + estimado <= self.tpm:
            return
        libre = usado
        for cuando, tokens in self._uso:
            libre -= tokens
            if libre + estimado <= self.tpm:
                espera = cuando + 60 - ahora + 1
                logger.info("Ritmo de tokens: espero {:.0f} s para no pasar de {} tokens/min", espera, self.tpm)
                self._dormir(max(espera, 0))
                return

    def completar(self, messages: list[dict], *, json_mode: bool = False, tools: list[dict] | None = None,
                  max_tokens: int = 3000, estimado: int = 6000, esfuerzo: str | None = None) -> Respuesta:
        extra: dict = {}
        esfuerzo = esfuerzo or os.getenv("GROQ_REASONING_EFFORT", "low")
        if self.modelo.startswith("openai/gpt-oss") and esfuerzo:
            extra["extra_body"] = {"reasoning_effort": esfuerzo}
        if json_mode:
            extra["response_format"] = {"type": "json_object"}
        if tools:
            extra["tools"], extra["tool_choice"] = tools, "required"

        for intento in range(1, MAX_REINTENTOS + 1):
            self._esperar(estimado)
            try:
                r = self.cliente.chat.completions.create(
                    model=self.modelo, messages=messages, temperature=0.2, max_tokens=max_tokens, **extra)
            except RateLimitError as exc:
                espera = _segundos_de_espera(exc)
                if "request too large" in str(exc).lower() or "too large" in str(exc).lower():
                    raise SolicitudMuyGrande("la petición supera el límite de tokens por minuto del plan") from exc
                logger.warning("429 de Groq (intento {}/{}): espero {:.0f} s", intento, MAX_REINTENTOS, espera)
                self._dormir(espera)
                continue
            except BadRequestError as exc:
                cuerpo = exc.body if isinstance(exc.body, dict) else {}
                error = cuerpo.get("error", cuerpo)
                if error.get("code") == "json_validate_failed" or "Failed to validate JSON" in str(error.get("message", "")):
                    # El modo JSON de Groq responde 400 si la salida no es JSON válido (p. ej. quedó cortada):
                    # se devuelve lo generado (o vacío) para que el llamador lo reintente, como hace el evaluador.
                    return Respuesta(error.get("failed_generation") or "", None, 0)
                raise VerificadorError(f"Groq rechazó la petición (400): {error.get('message', exc)}") from exc
            except APIStatusError as exc:
                if exc.status_code == 413:
                    raise SolicitudMuyGrande("la petición es demasiado grande para el plan") from exc
                if exc.status_code >= 500 and intento < MAX_REINTENTOS:
                    self._dormir(5 * intento)
                    continue
                raise VerificadorError(f"Groq respondió {exc.status_code}: {exc}") from exc
            except (APIConnectionError, APITimeoutError) as exc:
                if intento < MAX_REINTENTOS:
                    self._dormir(5 * intento)
                    continue
                raise VerificadorError(f"No se pudo conectar con Groq: {exc}") from exc

            tokens = getattr(getattr(r, "usage", None), "total_tokens", None) or 0
            self._uso.append((self._reloj(), tokens))
            logger.debug("Groq: {} tokens", tokens)
            mensaje = r.choices[0].message
            return Respuesta(mensaje.content or "", mensaje, tokens)
        raise VerificadorError("Groq siguió limitando tras varios reintentos; vuelve a intentar en unos minutos.")
