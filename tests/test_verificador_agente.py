"""Flujo completo del agente con un LLM simulado: qué entra al informe y qué rechaza el código."""
from __future__ import annotations

import json

from conftest import LlmFalso, cargar_caso, mensaje_con_busqueda

from ai.verifier import auditar_caso
from ai.verifier.informe import a_markdown, cargar, guardar
from test_verificador_calculo import BREAK_EVEN, EQUIDAD

URL = "https://www.alicorp.com.pe/pe/es/promociones/btl-cocineros-en-mercados"
PAGINA = "La promoción es organizada y financiada exclusivamente por Alicorp S.A.A. para su marca Cocinero."
CITA_CASO = "**Cocinero** (B-brand local): precio S/ 3.50"


def _llm_fmcg_01() -> LlmFalso:
    extraccion = {
        "chequeos": [
            dict(id="c1", **BREAK_EVEN),
            dict(id="c2", descripcion="inventada", variables={"a": {"valor": 9, "cita": "esta frase no existe en el caso 9"}},
                 calculo="a", afirmado={"valor": 9, "cita": "esta frase no existe en el caso 9", "decimales": 0}),
            {"id": "c3", "descripcion": "mal formado"},  # falta casi todo: el código lo descarta y lo reporta
        ],
        "hechos": [
            {"id": "h1", "afirmacion": "Cocinero es una marca de aceite de Alicorp", "tipo": "propiedad_marca", "cita_caso": CITA_CASO},
            {"id": "h2", "afirmacion": "hecho con cita inventada", "tipo": "otro", "cita_caso": "texto que el caso nunca dijo"},
        ],
    }
    veredicto = json.dumps({
        "veredicto": "contradicho", "resumen": "Cocinero es de Alicorp (2025).", "correccion_sugerida": "Cocinero es marca de Alicorp.",
        "fuentes": [{"titulo": "Alicorp", "url": URL, "cita": "financiada exclusivamente por Alicorp S.A.A. para su marca Cocinero"}]})
    informe = f"FUENTES:\n- {URL} | «financiada exclusivamente por Alicorp S.A.A. para su marca Cocinero» | respalda\nCONCLUSIÓN: contradicho."
    return LlmFalso(extraccion, {"Cocinero es una marca": (informe, mensaje_con_busqueda(URL, PAGINA, "BTL Cocinero | Alicorp"), veredicto)})


def test_auditoria_completa_detecta_defectos_y_rechaza_lo_inventado():
    informe = auditar_caso(cargar_caso("fmcg_01_lanzamiento_sku.json", con_defectos=True), llm=_llm_fmcg_01(), usar_cache=False)
    estados = {c.id: c.estado for c in informe.chequeos}
    assert estados == {"c1": "discrepancia", "c2": "descartado"}
    assert len(informe.hechos) == 1 and informe.hechos[0].veredicto == "contradicho"
    assert informe.hechos[0].fuentes[0].cita_verificada and informe.hechos[0].paginas_abiertas == [URL]
    assert any("c3" in d for d in informe.descartados) and any("h2" in d for d in informe.descartados)
    assert informe.veredicto_global == "revisar"
    assert informe.resumen["discrepancias"] == 1 and informe.resumen["hechos_contradichos"] == 1


def test_sin_web_no_hace_busquedas_y_lo_dice():
    llm = _llm_fmcg_01()
    informe = auditar_caso(cargar_caso("fmcg_01_lanzamiento_sku.json", con_defectos=True), con_web=False, llm=llm)
    assert informe.hechos == [] and all(not llamada["tools"] for llamada in llm.llamadas)
    assert any("sin web" in x for x in informe.limitaciones)


def test_caso_limpio_da_sin_hallazgos():
    extraccion = {"chequeos": [dict(id="c1", **EQUIDAD)], "hechos": []}
    informe = auditar_caso(cargar_caso("banca_01_credito_pyme.json"), llm=LlmFalso(extraccion), usar_cache=False)
    assert informe.veredicto_global == "sin_hallazgos" and informe.resumen["chequeos_ok"] == 1


def test_informe_se_guarda_y_se_vuelve_a_leer(tmp_path):
    informe = auditar_caso(cargar_caso("fmcg_01_lanzamiento_sku.json", con_defectos=True), llm=_llm_fmcg_01(), usar_cache=False)
    ruta_json, ruta_md = guardar(informe, tmp_path)
    assert cargar("fmcg_01", tmp_path) == informe
    md = ruta_md.read_text(encoding="utf-8")
    assert md == a_markdown(informe) and URL in md and "cita verificada" in md and "Corrección sugerida" in md


def test_si_el_agente_no_abre_ninguna_pagina_no_se_gasta_la_segunda_llamada():
    sin_paginas = mensaje_con_busqueda(URL, PAGINA)
    sin_paginas.model_extra["executed_tools"].pop()  # solo buscó, no abrió nada
    llm = _llm_fmcg_01()
    llm.hechos["Cocinero es una marca"] = ("Creo que sí es de Alicorp.", sin_paginas, "{}")
    informe = auditar_caso(cargar_caso("fmcg_01_lanzamiento_sku.json", con_defectos=True), llm=llm, usar_cache=False)
    hecho = informe.hechos[0]
    assert hecho.veredicto == "no_verificable" and "no abrió ninguna página" in hecho.nota
    assert not any(l["sistema"].startswith("Conviertes") for l in llm.llamadas)  # no hubo paso 2
    assert informe.veredicto_global == "revisar"  # por la discrepancia del break-even, no por el hecho


def test_un_hecho_que_llega_como_texto_no_se_pierde():
    extraccion = {"chequeos": [], "hechos": ["Cocinero es una marca de aceite de Alicorp"]}
    informe = auditar_caso(cargar_caso("fmcg_01_lanzamiento_sku.json", con_defectos=True), con_web=False,
                           llm=LlmFalso(extraccion), usar_cache=False)
    assert informe.descartados == []  # se aceptó como hecho; sin web no se verifica


def test_formas_raras_de_salida_del_modelo_no_rompen_la_auditoria():
    extraccion = {"chequeos": None, "hechos": {"h1": "esto debería ser una lista"}}
    informe = auditar_caso(cargar_caso("fmcg_01_lanzamiento_sku.json"), llm=LlmFalso(extraccion), usar_cache=False)
    assert informe.chequeos == [] and informe.hechos == [] and informe.veredicto_global == "sin_hallazgos"


def test_una_cache_con_forma_invalida_se_ignora_y_no_se_vuelve_a_servir(tmp_path, monkeypatch):
    from ai.verifier import extraccion
    monkeypatch.setattr(extraccion, "CACHE_DIR", tmp_path)
    caso = cargar_caso("banca_01_credito_pyme.json")
    llm = LlmFalso({"chequeos": [dict(id="c1", **EQUIDAD)], "hechos": []})
    auditar_caso(caso, con_web=False, llm=llm)  # llena la caché con una extracción válida
    (archivo,) = tmp_path.glob("extraccion_*.json")
    archivo.write_text("[1, 2, 3]", encoding="utf-8")  # se envenena la caché
    informe = auditar_caso(caso, con_web=False, llm=llm)
    assert informe.resumen["chequeos_ok"] == 1 and len(llm.llamadas) == 2  # volvió a pedirle al modelo
