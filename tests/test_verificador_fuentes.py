"""Guardarraíles de fuentes y cliente de Groq: sin cita verificada no hay veredicto."""
from __future__ import annotations

import httpx
import pytest
from conftest import mensaje_con_busqueda
from groq import APIStatusError, BadRequestError, RateLimitError

from ai.verifier.fuentes import aplicar_guardarrailes, extraer_json, limpiar_cita, normalizar_url, registro_desde
from ai.verifier.llm import LlmVerificador, SolicitudMuyGrande
from ai.verifier.modelos import RespuestaHecho

URL = "https://www.alicorp.com.pe/pe/es/promociones/btl-cocineros-en-mercados"
PAGINA = ("BTL Cocinero en Mercados\nLa Promoción es auspiciada, financiada y organizada exclusivamente por "
          "Alicorp S.A.A. para su marca Cocinero.")
BASE = dict(id="h1", afirmacion="Cocinero es una marca de Alicorp", tipo="propiedad_marca", fecha="2026-11-12")


def _respuesta(veredicto="confirmado", fuentes=None, **kw):
    return RespuestaHecho(veredicto=veredicto, resumen="r", fuentes=fuentes if fuentes is not None else [], **kw)


def _registro():
    return registro_desde(mensaje_con_busqueda(URL, PAGINA, "Alicorp"))


def test_registro_reconstruye_busquedas_y_paginas_abiertas():
    r = _registro()
    assert r.consultas == ["consulta de prueba"]
    assert r.conoce(URL + "/") and not r.conoce("https://inventada.com/x")
    assert "organizada exclusivamente por Alicorp" in r.texto_de(URL)


def test_confirmado_con_cita_textual_se_mantiene():
    fuente = {"titulo": "Alicorp", "url": URL, "cita": "organizada exclusivamente por Alicorp S.A.A. para su marca Cocinero"}
    v = aplicar_guardarrailes(_respuesta(fuentes=[fuente]), _registro(), **BASE)
    assert v.veredicto == "confirmado" and v.fuentes[0].cita_verificada and not v.nota


def test_cita_parafraseada_degrada_a_no_verificable():
    fuente = {"titulo": "Alicorp", "url": URL, "cita": "Cocinero pertenece a la empresa Alicorp desde hace años"}
    v = aplicar_guardarrailes(_respuesta(fuentes=[fuente]), _registro(), **BASE)
    assert v.veredicto == "no_verificable" and not v.fuentes[0].cita_verificada
    assert "ninguna cita textual" in v.nota


def test_url_que_el_agente_no_consulto_se_descarta():
    fuente = {"titulo": "Inventada", "url": "https://inventada.com/cocinero", "cita": "Cocinero es de Alicorp S.A.A."}
    v = aplicar_guardarrailes(_respuesta(fuentes=[fuente]), _registro(), **BASE)
    assert v.veredicto == "no_verificable" and v.fuentes == []
    assert "no figuran en lo que consultó" in v.nota


def test_veredicto_sin_ninguna_fuente_no_se_sostiene():
    assert aplicar_guardarrailes(_respuesta("contradicho"), _registro(), **BASE).veredicto == "no_verificable"


def test_fuente_solo_vista_en_resultados_no_basta_para_confirmar():
    solo_busqueda = mensaje_con_busqueda(URL, PAGINA)
    solo_busqueda.model_extra["executed_tools"].pop()  # sin apertura de página
    fuente = {"titulo": "x", "url": URL, "cita": "organizada exclusivamente por Alicorp S.A.A."}
    v = aplicar_guardarrailes(_respuesta(fuentes=[fuente]), registro_desde(solo_busqueda), **BASE)
    assert v.veredicto == "no_verificable"


def test_correccion_solo_se_conserva_si_el_veredicto_final_es_contradicho():
    fuente = {"titulo": "A", "url": URL, "cita": "organizada exclusivamente por Alicorp S.A.A. para su marca Cocinero"}
    conserva = aplicar_guardarrailes(_respuesta("contradicho", [fuente], correccion_sugerida="Es de Alicorp"), _registro(), **BASE)
    assert conserva.veredicto == "contradicho" and conserva.correccion_sugerida == "Es de Alicorp"
    degradado = aplicar_guardarrailes(_respuesta("contradicho", [], correccion_sugerida="Es de Alicorp"), _registro(), **BASE)
    assert degradado.correccion_sugerida is None


def test_no_verificable_no_exige_fuentes():
    assert aplicar_guardarrailes(_respuesta("no_verificable"), _registro(), **BASE).veredicto == "no_verificable"


def test_extraer_json_tolera_vallas_y_texto_alrededor():
    assert extraer_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extraer_json('Aquí va: {"a": {"b": 2}} fin') == {"a": {"b": 2}}
    with pytest.raises(ValueError):
        extraer_json("sin json")
    assert normalizar_url("HTTPS://A.com/x/#frag") == "https://a.com/x"


# ---------- Cliente de Groq: ritmo de tokens y errores ----------
class RelojFalso:
    def __init__(self):
        self.t, self.dormido = 1000.0, []

    def __call__(self):
        return self.t

    def dormir(self, s):
        self.dormido.append(s)
        self.t += s


class ClienteFalso:
    """Devuelve, en orden, lo que se le dé: respuestas o excepciones."""

    def __init__(self, *salidas):
        self.salidas = list(salidas)
        self.chat = type("C", (), {"completions": self})()

    def create(self, **kw):
        salida = self.salidas.pop(0)
        if isinstance(salida, Exception):
            raise salida
        return salida


def _ok(tokens=1000, texto="hola"):
    mensaje = type("M", (), {"content": texto})()
    return type("R", (), {"choices": [type("Ch", (), {"message": mensaje})()], "usage": type("U", (), {"total_tokens": tokens})()})()


def _http(status, **cabeceras):
    return httpx.Response(status, request=httpx.Request("POST", "https://api.groq.com/x"), headers=cabeceras)


def test_espera_para_no_pasar_de_8k_tokens_por_minuto():
    reloj = RelojFalso()
    llm = LlmVerificador(cliente=ClienteFalso(_ok(7000), _ok(7000)), dormir=reloj.dormir, reloj=reloj)
    llm.completar([{"role": "user", "content": "a"}], estimado=7000)
    llm.completar([{"role": "user", "content": "b"}], estimado=7000)
    assert len(reloj.dormido) == 1 and 55 <= reloj.dormido[0] <= 62  # esperó a que la ventana de 60 s liberara tokens


def test_reintenta_tras_429_respetando_retry_after():
    reloj = RelojFalso()
    error = RateLimitError("rate limit", response=_http(429, **{"retry-after": "4"}), body=None)
    llm = LlmVerificador(cliente=ClienteFalso(error, _ok(texto="listo")), dormir=reloj.dormir, reloj=reloj)
    assert llm.completar([{"role": "user", "content": "a"}], estimado=100).contenido == "listo"
    assert 4 in reloj.dormido


def test_peticion_muy_grande_no_se_reintenta():
    error = APIStatusError("Request too large", response=_http(413), body=None)
    llm = LlmVerificador(cliente=ClienteFalso(error), dormir=lambda s: None)
    with pytest.raises(SolicitudMuyGrande):
        llm.completar([{"role": "user", "content": "a"}], estimado=100)


@pytest.mark.parametrize("cuerpo, esperado", [
    ({"error": {"code": "json_validate_failed", "failed_generation": '{"a": 1'}}, '{"a": 1'),
    ({"error": {"message": "Failed to validate JSON. Please adjust your prompt."}}, ""),
])
def test_json_invalido_de_groq_se_devuelve_para_reintentar(cuerpo, esperado):
    error = BadRequestError("400", response=_http(400), body=cuerpo)
    llm = LlmVerificador(cliente=ClienteFalso(error), dormir=lambda s: None)
    assert llm.completar([{"role": "user", "content": "a"}], json_mode=True, estimado=100).contenido == esperado


def test_json_que_no_es_un_objeto_se_rechaza_para_reintentar():
    with pytest.raises(ValueError, match="no un objeto"):
        extraer_json('[{"id": "c1"}]')


def test_cita_fusionada_con_un_comentario_se_limpia_antes_de_verificar():
    assert limpiar_cita("«organizada exclusivamente por Alicorp» | confirma que es suya (2025)") == "organizada exclusivamente por Alicorp"
    assert limpiar_cita("texto sin comillas") == "texto sin comillas"
    fusionada = {"titulo": "Alicorp", "url": URL,
                 "cita": "«organizada exclusivamente por Alicorp S.A.A. para su marca Cocinero» | confirma que Cocinero es de Alicorp"}
    v = aplicar_guardarrailes(_respuesta(fuentes=[fusionada]), _registro(), **BASE)
    assert v.veredicto == "confirmado" and v.fuentes[0].cita_verificada
    inventada = dict(fusionada, cita="«Cocinero fue vendida a un fondo de inversión en 1998» | confirma la venta")
    assert aplicar_guardarrailes(_respuesta(fuentes=[inventada]), _registro(), **BASE).veredicto == "no_verificable"
