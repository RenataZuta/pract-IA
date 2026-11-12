"""
Agente verificador de casos.

Audita un caso de PractIA en tres pasos y deja un informe con fuentes:

1. Un LLM *lista* qué se puede comprobar (cuentas y hechos del mundo real); no juzga.
2. El código *calcula*: las cuentas las hace `calculo.py`, nunca el modelo.
3. Un LLM con búsqueda web *verifica* cada hecho; `fuentes.py` rechaza todo veredicto
   que no tenga una cita textual encontrada en una página que el agente abrió de verdad.

El agente propone; nunca edita los casos. Ver docs/AGENTE_VERIFICADOR.md.
"""
from ai.verifier.agente import auditar_caso, auditar_texto
from ai.verifier.modelos import Informe

__all__ = ["auditar_caso", "auditar_texto", "Informe"]
