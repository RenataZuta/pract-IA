"""Configuración común de las pruebas: el repo en el path y utilidades para casos y LLM falsos."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

FIXTURES = ROOT / "tests" / "fixtures" / "casos_con_defectos"


def cargar_caso(nombre: str, con_defectos: bool = False) -> dict:
    ruta = (FIXTURES if con_defectos else ROOT / "ai" / "cases") / nombre
    return json.loads(ruta.read_text(encoding="utf-8"))


def mensaje_con_busqueda(url: str, texto_pagina: str, titulo: str = "Página") -> SimpleNamespace:
    """Un mensaje de Groq con `executed_tools`: una búsqueda y la apertura de una página."""
    return SimpleNamespace(content="", model_extra={"executed_tools": [
        {"name": "browser.search", "type": "browser_search", "arguments": json.dumps({"query": "consulta de prueba"}),
         "output": "", "search_results": {"results": [{"title": titulo, "url": url, "content": ""}]}},
        {"name": "browser.open", "type": "browser.open", "arguments": "{}", "output": "",
         "search_results": {"results": [{"title": titulo, "url": url, "content": "L0: \n" + "\n".join(
             f"L{i + 1}: {linea}" for i, linea in enumerate(texto_pagina.splitlines()))}]}},
    ]})


class LlmFalso:
    """Sustituye a LlmVerificador: devuelve respuestas guionadas y anota lo que se le pidió.

    `hechos` mapea un texto de la afirmación a (informe en prosa, mensaje con executed_tools, veredicto JSON).
    """

    modelo = "modelo-falso"

    def __init__(self, extraccion: dict | None = None, hechos: dict[str, tuple[str, SimpleNamespace, str]] | None = None):
        self.extraccion, self.hechos, self.llamadas = extraccion or {}, hechos or {}, []

    def completar(self, messages, *, json_mode=False, tools=None, max_tokens=0, estimado=0, esfuerzo=None):
        from ai.verifier.llm import Respuesta
        self.llamadas.append({"json_mode": json_mode, "tools": tools, "sistema": messages[0]["content"][:20]})
        if json_mode and messages[0]["content"].startswith("Conviertes"):  # paso 2: estructurar el informe
            usuario = messages[1]["content"]
            for clave, (_, _, veredicto) in self.hechos.items():
                if clave in usuario:
                    return Respuesta(veredicto, None, 50)
            raise AssertionError(f"veredicto no guionado para: {usuario[:80]}")
        if json_mode:  # extracción de qué comprobar
            return Respuesta(json.dumps(self.extraccion), None, 100)
        usuario = messages[-1]["content"]  # paso 1: investigar con la búsqueda
        for clave, (informe, mensaje, _) in self.hechos.items():
            if clave in usuario:
                return Respuesta(informe, mensaje, 100)
        raise AssertionError(f"investigación no guionada para: {usuario[:80]}")


@pytest.fixture
def llm_falso():
    return LlmFalso
