"""La ficha de verificación aparece en la app y nunca rompe la vista del caso."""
from __future__ import annotations

import pytest
from conftest import cargar_caso
from streamlit.testing.v1 import AppTest
from test_verificador_agente import _llm_fmcg_01

from ai.verifier import auditar_caso

ETIQUETA = "Verificación del caso por el agente"


def _abrir_caso(texto_del_caso: str) -> AppTest:
    at = AppTest.from_file("app/main.py", default_timeout=40).run()
    at.sidebar.selectbox[0].set_value("FMCG").run()
    caso = next(o for o in at.sidebar.selectbox[1].options if texto_del_caso in o)
    return at.sidebar.selectbox[1].set_value(caso).run()


@pytest.fixture
def informe_demo():
    return auditar_caso(cargar_caso("fmcg_01_lanzamiento_sku.json", con_defectos=True), llm=_llm_fmcg_01(), usar_cache=False)


def test_la_ficha_se_muestra_con_fuentes_y_enlaces(monkeypatch, informe_demo):
    monkeypatch.setattr("ai.verifier.informe.cargar", lambda caso_id: informe_demo)
    at = _abrir_caso("Primor")
    assert not at.exception
    ficha = [e for e in at.expander if ETIQUETA in e.label]
    assert len(ficha) == 1 and "por revisar" in ficha[0].label
    texto = " ".join(m.value for m in ficha[0].markdown)
    assert "alicorp.com.pe" in texto and "cita verificada" in texto and "contradicho" in texto


def test_sin_informe_no_se_pinta_nada(monkeypatch):
    monkeypatch.setattr("ai.verifier.informe.cargar", lambda caso_id: None)
    at = _abrir_caso("Primor")
    assert not at.exception and not [e for e in at.expander if ETIQUETA in e.label]


def test_un_informe_corrupto_no_rompe_el_caso(monkeypatch):
    def corrupto(caso_id):
        raise ValueError("JSON roto")
    monkeypatch.setattr("ai.verifier.informe.cargar", corrupto)
    at = _abrir_caso("Primor")
    assert not at.exception and any("Anexo 1" in e.label for e in at.expander)  # el caso sigue completo
