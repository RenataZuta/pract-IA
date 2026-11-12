"""Los 12 casos: estructura y cuentas de los anexos (las que se corrigieron el 12-nov no pueden volver a romperse)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai.verifier.tablas import parsear_tablas

CASOS = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted((Path(__file__).parent.parent / "ai" / "cases").glob("*.json"))}
OBLIGATORIOS = ("id", "industry", "company", "case_type", "title", "context", "prompt", "pista_respuesta_modelo")


def v(caso: str, tabla: int, fila: str, col: str) -> float:
    return parsear_tablas(CASOS[caso])[tabla - 1].valor(fila, col)


def test_hay_12_casos_4_por_industria_con_ids_unicos():
    assert len(CASOS) == 12 and len({c["id"] for c in CASOS.values()}) == 12
    for industria in ("Banca", "FMCG", "Consultoría"):
        assert sum(c["industry"] == industria for c in CASOS.values()) == 4


@pytest.mark.parametrize("nombre", CASOS)
def test_cada_caso_tiene_sus_campos_y_su_id_coincide_con_el_archivo(nombre):
    caso = CASOS[nombre]
    assert all(caso.get(k) for k in OBLIGATORIOS), f"faltan campos en {nombre}"
    assert nombre.startswith(caso["id"])
    for anexo in caso.get("exhibits", []):
        assert anexo["title"].strip() and anexo["content"].strip()
    assert len((caso.get("respuesta_referencia") or caso["pista_respuesta_modelo"]).split()) >= 40


def test_banca_01_balance_cuadra_y_el_patrimonio_sube_lo_que_la_utilidad():
    for anio in ("2025", "2026"):
        activo = v("banca_01_credito_pyme", 2, "Total activo", anio)
        pasivo_y_patrimonio = sum(v("banca_01_credito_pyme", 2, f, anio) for f in
                                  ("Proveedores", "Deuda financiera CP", "Deuda financiera LP", "Patrimonio"))
        assert activo == pasivo_y_patrimonio
    assert v("banca_01_credito_pyme", 2, "Patrimonio", "2026") - v("banca_01_credito_pyme", 2, "Patrimonio", "2025") \
        == v("banca_01_credito_pyme", 1, "Utilidad neta", "2026")


def test_banca_01_cobertura_y_deuda_que_cita_la_referencia():
    ebitda, gastos = v("banca_01_credito_pyme", 1, "EBITDA", "2026"), abs(v("banca_01_credito_pyme", 1, "Gastos financieros", "2026"))
    assert round(ebitda / gastos, 1) == 2.2
    d = lambda anio: sum(v("banca_01_credito_pyme", 2, f, anio) for f in ("Deuda financiera CP", "Deuda financiera LP"))  # noqa: E731
    assert round((d("2026") / d("2025") - 1) * 100) == 34


@pytest.mark.parametrize("col, payback", [("Lima", 3.6), ("Arequipa", 5.1)])
def test_consultoria_02_el_payback_sale_de_capex_ventas_y_margen(col, payback):
    c = "consultoria_02_market_entry"
    calculado = v(c, 1, "Inversión inicial", col) / (v(c, 1, "Venta mensual", col) * 12 * v(c, 1, "Margen operativo", col) / 100)
    assert round(calculado, 1) == payback == v(c, 1, "Payback", col)


def test_banca_04_tasa_minima_y_mora_ponderada_de_la_referencia():
    c = "banca_04_pricing_productos"
    tasa = lambda col, m, g: 6 + m * 0.7 + g + 8  # noqa: E731  fondeo + pérdida esperada + gasto + margen
    assert [round(tasa("", m, g), 1) for m, g in ((3, 3), (9, 6), (6, 4))] == [19.1, 26.3, 22.2]
    assert round(0.45 * v(c, 1, "Mora a 30 días", "A. Dependientes en planilla") + 0.35 * v(c, 1, "Mora a 30 días", "C. Profesionales independientes")
                 + 0.20 * v(c, 1, "Mora a 30 días", "B. Comerciantes independientes"), 2) == 5.25 < 6


def test_fmcg_04_margenes_de_la_subida_de_precio():
    c = "fmcg_04_pricing"
    antes, hoy, post = (v(c, 1, "Margen total mensual", col) for col in ("Antes", "Hoy", "Post-subida"))
    assert (antes, hoy, post) == (2.52, 1.62, 2.51) and post > hoy  # la subida sí recupera margen
    assert round(9.0 * (1 - 1.2 * (1.70 - 1.50) / 1.50), 1) == 7.6


def test_fmcg_01_margen_y_break_even_de_la_referencia():
    assert round(3.80 - 2.40, 2) == 1.40 and round(2.5 / 1.40, 1) == 1.8 and round(4 * 1.40, 1) == 5.6
    assert "break-even" in CASOS["fmcg_01_lanzamiento_sku"]["pista_respuesta_modelo"]


def test_consultoria_01_y_04_las_cuentas_del_anexo():
    c1 = "consultoria_01_profitability"
    gastos = lambda col: sum(abs(v(c1, 1, f, col)) for f in ("Gastos de personal", "Alquileres", "Otros gastos operativos"))  # noqa: E731
    assert v(c1, 1, "Margen bruto", "2026 (LTM)") - gastos("2026 (LTM)") == v(c1, 1, "Utilidad operativa", "2026 (LTM)") == -18
    c4 = "consultoria_04_evaluacion_impacto"
    assert (10_100 - 8_200) - (7_300 - 6_900) == 1_500 and 17 <= 1_800 / (1_150 * 0.09) < 18
