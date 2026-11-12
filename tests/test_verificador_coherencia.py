"""Coherencia del feedback con el caso: las cifras deben salir del contexto o los anexos."""
from __future__ import annotations

from conftest import cargar_caso

from ai.evaluator import ComparativoReferencia, CriterionScore, Feedback
from ai.verifier.coherencia import revisar_feedback


def _feedback(**kw) -> Feedback:
    base = dict(puntaje_total=70, criterios=[CriterionScore(nombre="Uso de números", puntaje=8, comentario="Usó bien los números.")],
                fortaleza_principal="Estructura clara.", tres_cosas_a_mejorar=["Más detalle."], respuesta_modelo="Aprobar.")
    return Feedback(**{**base, **kw})


def test_cifras_del_caso_no_generan_alertas():
    f = _feedback(criterios=[CriterionScore(nombre="Uso de números", puntaje=8,
                  comentario="Citó que el EBITDA bajó de 730 a 560 mil y que la línea es de S/ 1,200,000. Puntaje 8/10.")])
    assert revisar_feedback(f, cargar_caso("banca_01_credito_pyme.json")) == []


def test_cifra_ajena_al_caso_se_senala_con_su_ubicacion():
    f = _feedback(tres_cosas_a_mejorar=["Mencionar que la deuda subió 87% y que el EBITDA fue 561 mil."],
                  comparativo_referencia=ComparativoReferencia(le_falto=["No cubrió la garantía de S/ 4,500,000"]))
    alertas = revisar_feedback(f, cargar_caso("banca_01_credito_pyme.json"))
    cifras = {a.cifra for a in alertas}
    assert {"87%", "561 mil", "4,500,000"} <= cifras
    assert any("cosa a mejorar" in a.donde for a in alertas) and any("le faltó" in a.donde for a in alertas)


def test_puntajes_anios_y_conteos_chicos_no_se_contrastan():
    f = _feedback(fortaleza_principal="Sacó 85/100 en 2026 y dio 3 razones en 2 minutos.")
    assert revisar_feedback(f, cargar_caso("banca_01_credito_pyme.json")) == []


def test_la_rubrica_compacta_conserva_todo_su_contenido():
    import json

    from ai.evaluator import _format_rubric
    rubrica = json.loads((cargar_caso.__globals__["ROOT"] / "ai" / "rubrics" / "banca.json").read_text(encoding="utf-8"))
    enviado = json.loads(_format_rubric(rubrica, ()))
    assert [c["nombre"] for c in enviado["criterios"]] == [c["nombre"] for c in rubrica["criterios"]]
    for original, c in zip(rubrica["criterios"], enviado["criterios"]):
        assert c["descripcion"] == original["descripcion"] and c["peso_pct"] == round(original["peso"] * 100, 1)
        assert c.get("ejemplos_alto", "") == original.get("ejemplos_alto", "")
        assert c.get("ejemplos_bajo", "") == original.get("ejemplos_bajo", "")
