"""Plan B del micrófono: la respuesta de referencia entra como transcripción y el flujo evalúa."""
from __future__ import annotations

from streamlit.testing.v1 import AppTest

from ai.evaluator import ComparativoReferencia, CriterionScore, Feedback


def _feedback_falso(*args, **kwargs) -> Feedback:
    return Feedback(
        puntaje_total=72,
        criterios=[CriterionScore(nombre="Uso de números y anexos", puntaje=7, comentario="Usó el 34% del anexo.", tipo="tecnico", peso=1.0)],
        comparativo_referencia=ComparativoReferencia(coincide=["Aprobó con condiciones"]),
        fortaleza_principal="Estructura clara.", tres_cosas_a_mejorar=["a", "b", "c"], respuesta_modelo="Aprobar.",
        puntaje_por_tipo={"tecnico": 72})


def _abrir():
    at = AppTest.from_file("app/main.py", default_timeout=60).run()
    return at


def test_el_boton_carga_la_referencia_y_permite_evaluar(monkeypatch):
    llamadas = []
    monkeypatch.setattr("ai.evaluator.evaluate_response", lambda *a, **k: (llamadas.append(1), _feedback_falso())[1])
    at = _abrir()
    assert not at.text_area  # sin audio no hay caja de transcripción
    at.button(key="usar_ejemplo").click().run()
    assert not at.exception
    caja = at.text_area[0]
    assert "Recomiendo aprobar" in caja.value  # la respuesta de referencia de banca_01
    assert any("respuesta de referencia del caso" in i.value for i in at.info)

    evaluar = next(b for b in at.button if b.label == "Evaluar respuesta")
    evaluar.click().run()
    assert not at.exception and len(llamadas) == 1
    assert any("72/100" in m.value for m in at.metric) or any(m.value == "72/100" for m in at.metric)

    # Evaluar otra vez el mismo texto no vuelve a llamar a Groq
    next(b for b in at.button if b.label == "Evaluar respuesta").click().run()
    assert len(llamadas) == 1 and any("ya está evaluada" in i.value for i in at.info)
