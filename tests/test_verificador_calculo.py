"""Motor de cálculo del verificador: tablas, intérprete seguro, citas y regresión con defectos reales."""
from __future__ import annotations

import pytest
from conftest import cargar_caso

from ai.verifier.calculo import ErrorExpresion, evaluar, evaluar_chequeo
from ai.verifier.citas import cita_en_texto, numero_en_cita, valor_en_contexto
from ai.verifier.extraccion import texto_de_afirmaciones, texto_del_caso
from ai.verifier.modelos import ChequeoNumerico
from ai.verifier.tablas import ErrorCelda, a_numero, parsear_tablas


@pytest.mark.parametrize("celda, esperado", [
    ("8,400", 8400), ("(6,300)", -6300), ("-18", -18), ("**560**", 560), ("S/ 320K", 320_000),
    ("S/ 1.1M", 1_100_000), ("24%", 24), ("3.5 años", 3.5), ("+2,800", 2800), ("USD 8,500", 8500),
    ("36-60 meses", None), ("Promart", None), ("", None), ("—", None), ("38", 38),
])
def test_a_numero(celda, esperado):
    assert a_numero(celda) == esperado


def test_tablas_numeradas_y_celdas():
    tablas = parsear_tablas(cargar_caso("banca_01_credito_pyme.json"))
    assert [t.indice for t in tablas] == [1, 2]
    assert tablas[0].valor("Ventas", "2026") == 10_100  # la columna es "2026 (LTM)": se acepta el prefijo
    assert tablas[1].valor("Patrimonio", "2026") == 2070
    assert tablas[1].valor("Total activo", "2025") == 4030  # fila en negrita


def test_celda_inexistente_o_no_numerica_da_error_claro():
    t = parsear_tablas(cargar_caso("banca_01_credito_pyme.json"))[0]
    with pytest.raises(ErrorCelda, match="no existe la fila"):
        t.valor("Ingresos fantasma", "2026")
    with pytest.raises(ErrorCelda, match="no existe la columna"):
        t.valor("Ventas", "2031")


@pytest.mark.parametrize("expr, esperado", [
    ("730/210", 730 / 210), ("(a+b)*2 - abs(-3)", 7), ("max(1,2,3)**2", 9), ("-a + +b", 1), ("round(2.567, 1)", 2.6),
])
def test_evaluar_aritmetica(expr, esperado):
    assert evaluar(expr, {"a": 2, "b": 3}) == pytest.approx(esperado)


@pytest.mark.parametrize("expr", [
    "__import__('os').system('echo hola')", "().__class__", "a.real", "open('x')", "'a' * 3", "2 ** 99",
    "1/0", "lambda: 1", "[1, 2]", "desconocida + 1", "print(1)", "a if a else b", "1 +", "1+" * 70 + "1",
    "x" * 300,
])
def test_evaluar_rechaza_todo_lo_que_no_sea_aritmetica(expr):
    with pytest.raises(ErrorExpresion):
        evaluar(expr, {"a": 2, "b": 3})


def test_citas_toleran_formato_no_parafrasis():
    texto = "| **Total activo** | **4,960** |\nEl break-even requiere vender **4 millones de unidades/año**."
    assert cita_en_texto("Total activo | 4,960", texto)
    assert cita_en_texto("break-even requiere vender 4 millones de unidades/año", texto)
    assert not cita_en_texto("necesita vender 9 millones de unidades por año", texto)
    assert not cita_en_texto("corta", texto)  # demasiado corta para probar algo
    assert numero_en_cita(4960, "Total activo | 4,960") and numero_en_cita(2.5, "S/ 2.5 millones")
    assert not numero_en_cita(7, "S/ 2.5 millones")


# ---------- Regresión: los defectos reales de los casos antes del commit 384710b ----------
def _chequeo(**kw) -> ChequeoNumerico:
    return ChequeoNumerico.model_validate({"id": "c1", "descripcion": "prueba", **kw})


def _evaluar(caso: dict, chequeo: ChequeoNumerico):
    return evaluar_chequeo(chequeo, parsear_tablas(caso), texto_del_caso(caso))


EQUIDAD = dict(
    descripcion="La variación del patrimonio debe igualar la utilidad neta si no hay aportes ni dividendos",
    variables={"p26": {"tabla": 2, "fila": "Patrimonio", "columna": "2026"},
               "p25": {"tabla": 2, "fila": "Patrimonio", "columna": "2025"},
               "un": {"tabla": 1, "fila": "Utilidad neta", "columna": "2026"}},
    calculo="p26 - p25", afirmado={"expresion": "un"})


def test_detecta_patrimonio_inconsistente_y_acepta_el_caso_corregido():
    malo = _evaluar(cargar_caso("banca_01_credito_pyme.json", con_defectos=True), _chequeo(**EQUIDAD))
    assert (malo.estado, malo.severidad, malo.calculado, malo.afirmado) == ("discrepancia", "alta", 290, 210)
    bueno = _evaluar(cargar_caso("banca_01_credito_pyme.json"), _chequeo(**EQUIDAD))
    assert bueno.estado == "ok"


def _payback(columna: str) -> dict:
    celda = lambda fila: {"tabla": 1, "fila": fila, "columna": columna}  # noqa: E731  (en ese caso el anexo 1 son viñetas)
    return dict(descripcion=f"Payback de {columna} = CAPEX / (venta anual x margen)",
                variables={"capex": celda("Inversión inicial (CAPEX)"), "venta": celda("Venta mensual promedio"),
                           "m": celda("Margen operativo tienda"), "pb": celda("Payback típico")},
                calculo="capex / (venta * 12 * m / 100)", afirmado={"expresion": "pb"})


def test_detecta_payback_que_no_sale_de_margen_y_capex():
    malo = _evaluar(cargar_caso("consultoria_02_market_entry.json", con_defectos=True), _chequeo(**_payback("Lima")))
    assert malo.estado == "discrepancia" and malo.severidad == "alta"
    assert malo.calculado == pytest.approx(1.59, abs=0.01) and malo.afirmado == 3.5
    for columna in ("Lima", "Arequipa"):
        assert _evaluar(cargar_caso("consultoria_02_market_entry.json"), _chequeo(**_payback(columna))).estado == "ok"


BREAK_EVEN = dict(
    descripcion="El break-even de la inversión es CAPEX / margen unitario",
    variables={"capex": {"valor": 2.5, "cita": "S/ 2.5 millones"},
               "margen": {"valor": 1.4, "cita": "Margen contribución: S/ 1.40/unidad"}},
    calculo="capex / margen",
    afirmado={"valor": 4, "cita": "break-even requiere vender 4 millones de unidades/año", "decimales": 0})


def test_detecta_break_even_incoherente_y_descarta_la_cita_en_el_caso_corregido():
    malo = _evaluar(cargar_caso("fmcg_01_lanzamiento_sku.json", con_defectos=True), _chequeo(**BREAK_EVEN))
    assert malo.estado == "discrepancia" and malo.severidad == "alta"
    assert malo.calculado == pytest.approx(1.79, abs=0.01)
    # En el caso corregido esa frase ya no existe: el chequeo no se puede sostener y se descarta.
    assert _evaluar(cargar_caso("fmcg_01_lanzamiento_sku.json"), _chequeo(**BREAK_EVEN)).estado == "descartado"


def test_cita_inventada_o_numero_ajeno_a_su_cita_descartan_el_chequeo():
    caso = cargar_caso("banca_01_credito_pyme.json")
    inventada = dict(EQUIDAD, afirmado={"valor": 99, "cita": "el patrimonio subió 99 millones", "decimales": 0})
    assert _evaluar(caso, _chequeo(**inventada)).estado == "descartado"
    ajeno = dict(EQUIDAD, afirmado={"valor": 99, "cita": "Total activo", "decimales": 0})
    assert "no aparece en el caso junto a" in _evaluar(caso, _chequeo(**ajeno)).detalle


def _crecimiento_deuda(calculo: str):
    celda = lambda fila, anio: {"tabla": 2, "fila": fila, "columna": anio}  # noqa: E731
    return _chequeo(
        descripcion="Crecimiento de la deuda financiera total",
        variables={"c26": celda("Deuda financiera CP", "2026"), "l26": celda("Deuda financiera LP", "2026"),
                   "c25": celda("Deuda financiera CP", "2025"), "l25": celda("Deuda financiera LP", "2025")},
        calculo=calculo,
        afirmado={"valor": 34, "cita": "Deuda financiera total creció 34% en un año", "decimales": 0})


def test_deuda_total_crecio_34_por_ciento():
    caso = cargar_caso("banca_01_credito_pyme.json")
    r = _evaluar(caso, _crecimiento_deuda("((c26 + l26) / (c25 + l25) - 1) * 100"))
    assert r.estado == "ok" and r.calculado == pytest.approx(33.6, abs=0.05)


def test_diferencia_de_unidades_no_se_reporta_como_error_del_caso():
    # El modelo olvidó multiplicar por 100: 0.336 contra 34 es un problema de unidades, no del caso.
    r = _evaluar(cargar_caso("banca_01_credito_pyme.json"), _crecimiento_deuda("(c26 + l26) / (c25 + l25) - 1"))
    assert r.estado == "no_evaluable" and "unidades" in r.detalle


def test_chequeo_trivial_que_solo_copia_un_numero_se_descarta():
    caso = cargar_caso("fmcg_01_lanzamiento_sku.json", con_defectos=True)
    trivial = _chequeo(descripcion="break-even", variables={"a": {"valor": 4, "cita": "break-even requiere vender 4 millones de unidades/año"}},
                       calculo="a", afirmado={"valor": 4, "cita": "break-even requiere vender 4 millones de unidades/año", "decimales": 0})
    r = _evaluar(caso, trivial)
    assert r.estado == "descartado" and "trivial" in r.detalle  # antes salía "ok" sin haber comprobado nada


def test_numero_en_cita_acepta_conversion_de_unidades_pero_no_numeros_ajenos():
    assert numero_en_cita(4_000_000, "vender 4 millones de unidades/año")  # "4 millones" -> 4000000
    assert numero_en_cita(0.37, "Margen contribución: S/ 1.40/unidad (37%)")  # 37% -> 0.37
    assert numero_en_cita(1500, "S/ 1.5 mil")
    assert not numero_en_cita(7, "S/ 2.5 millones") and not numero_en_cita(4_100_000, "vender 4 millones")


def test_cita_con_puntos_suspensivos_se_verifica_por_fragmentos():
    pagina = "Primor es una marca premium y líder de la categoría.\nOtro párrafo.\nDentro de su portafolio, cuenta con dos variedades."
    assert cita_en_texto("Primor es una marca premium y líder de la categoría… Dentro de su portafolio, cuenta con dos variedades", pagina)
    assert not cita_en_texto("Primor es una marca premium y líder de la categoría… y pertenece a un fondo extranjero desde 1990", pagina)


def test_numero_se_ancla_en_su_contexto_y_tolera_ceros_y_parafrasis():
    texto = "El margen de contribución es S/ 1.40/unidad. Se proyectan 4 millones de unidades/año."
    assert valor_en_contexto(1.4, "margen de S/ 1.40 por unidad", texto)  # 1.4 == 1.40 y cita parafraseada
    assert valor_en_contexto(4_000_000, "proyectan 4 millones de unidades", texto)
    assert not valor_en_contexto(9, "margen de contribución por unidad", texto)  # el 9 no está en el texto
    assert not valor_en_contexto(4, "el break-even exige vender 4 hectáreas de cacao", texto)  # 4 existe, el contexto no


def test_constantes_universales_no_necesitan_estar_en_el_caso():
    caso = cargar_caso("consultoria_02_market_entry.json", con_defectos=True)
    celda = lambda fila: {"tabla": 1, "fila": fila, "columna": "Lima"}  # noqa: E731
    chq = _chequeo(descripcion="payback con 12 meses", calculo="capex / (venta * meses * m / 100)",
                   variables={"capex": celda("Inversión inicial (CAPEX)"), "venta": celda("Venta mensual promedio"),
                              "m": celda("Margen operativo tienda"), "meses": {"valor": 12, "cita": "12 meses al año"},
                              "pb": celda("Payback típico")},
                   afirmado={"expresion": "pb"})
    assert _evaluar(caso, chq).estado == "discrepancia"  # no se descartó por la cita de "12 meses al año"


def test_leer_una_celda_y_compararla_con_el_mismo_anexo_no_cuenta_como_chequeo():
    caso = cargar_caso("consultoria_02_market_entry.json", con_defectos=True)
    lectura = _chequeo(descripcion="El margen de Lima es 18%", variables={"m": {"tabla": 1, "fila": "Margen operativo tienda", "columna": "Lima"}},
                       calculo="m", afirmado={"valor": 18, "cita": "Margen operativo tienda 18%", "decimales": 0})
    r = evaluar_chequeo(lectura, parsear_tablas(caso), texto_del_caso(caso), texto_de_afirmaciones(caso))
    assert r.estado == "descartado" and "lectura de una celda" in r.detalle


def test_la_precision_de_un_numero_escrito_en_millones_es_en_millones():
    caso = cargar_caso("consultoria_02_market_entry.json", con_defectos=True)
    chq = _chequeo(descripcion="mercado accesible ~S/ 3M al mes",
                   variables={"p": {"valor": 68, "cita": "68K del NSE A/B+"}},
                   calculo="p * 1000 * 2 * 22", afirmado={"valor": 3_000_000, "cita": "~S/ 3M/mes de mercado accesible", "decimales": 0})
    r = _evaluar(caso, chq)  # 2,992,000 contra "3M": dentro de la precisión con que se escribió
    assert r.estado == "ok" and r.calculado == 2_992_000
