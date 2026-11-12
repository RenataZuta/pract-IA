"""Los errores de Groq llegan al estudiante como mensajes claros, no como texto crudo de la excepción."""
from __future__ import annotations

import json

import httpx
import pytest
from groq import APIConnectionError, APIStatusError, AuthenticationError, RateLimitError

from ai.errores_groq import explicar


def _resp(status, **h):
    return httpx.Response(status, request=httpx.Request("POST", "https://api.groq.com/x"), headers=h)


@pytest.mark.parametrize("exc, contiene", [
    (RateLimitError("Rate limit reached ... tokens per minute. Please try again in 12.3s", response=_resp(429), body=None), "12 segundos"),
    (RateLimitError("429", response=_resp(429, **{"retry-after": "4"}), body=None), "4 segundos"),
    (RateLimitError("Limit 200000 ... tokens per day (TPD)", response=_resp(429), body=None), "cupo diario"),
    (RateLimitError("Request too large for model", response=_resp(429), body=None), "demasiado grande"),
    (RateLimitError("429 sin detalle", response=_resp(429), body=None), "un minuto"),
    (AuthenticationError("401", response=_resp(401), body=None), "no es válida"),
    (APIStatusError("The model has been decommissioned", response=_resp(404), body=None), "ya no está disponible"),
    (APIStatusError("boom", response=_resp(503), body=None), "problema temporal"),
    (APIConnectionError(request=httpx.Request("POST", "https://api.groq.com/x")), "No hay conexión"),
])
def test_cada_error_se_explica(exc, contiene):
    assert contiene in explicar(exc)


def test_un_error_desconocido_conserva_el_detalle():
    assert "algo raro" in explicar(RuntimeError("algo raro"))


def test_el_evaluador_devuelve_el_mensaje_claro_ante_un_429(monkeypatch):
    from ai import evaluator

    class GroqLimitado:
        def __init__(self, **kw):
            self.chat = type("C", (), {"completions": self})()

        def create(self, **kw):
            raise RateLimitError("try again in 30s", response=_resp(429), body=None)

    monkeypatch.setenv("GROQ_API_KEY", "gsk_de_prueba")
    monkeypatch.setattr(evaluator, "Groq", GroqLimitado)
    caso = json.loads((evaluator.PROMPTS_DIR.parent / "cases" / "banca_01_credito_pyme.json").read_text(encoding="utf-8"))
    rubrica = json.loads((evaluator.PROMPTS_DIR.parent / "rubrics" / "banca.json").read_text(encoding="utf-8"))
    with pytest.raises(evaluator.EvaluationError, match="Espera unos 30 segundos"):
        evaluator.evaluate_response("Recomiendo aprobar con condiciones.", caso, rubrica)


def test_sin_key_el_mensaje_dice_donde_ponerla(monkeypatch):
    from ai import evaluator
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(evaluator.EvaluationError, match="Secrets"):
        evaluator.evaluate_response("texto", {}, {})
