"""
Coherencia del feedback con el caso: ¿las cifras que el evaluador menciona salen del contexto y los anexos?

Es una revisión determinista (sin LLM, sin tokens): recorre los textos del feedback, extrae las cifras y comprueba
que cada una exista en el caso (tal cual, con otra escala o como porcentaje). Una cifra que no está puede ser un
cálculo legítimo del evaluador (un ratio, una diferencia) o una invención: el sistema solo la señala, no decide.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from ai.verifier.citas import UNIVERSALES, valor_en_contexto
from ai.verifier.extraccion import texto_del_caso

_CIFRA = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)\s*(%|x\b|millones|mil\b|[MK]\b)?", re.I)
_PUNTAJE = re.compile(r"^\s*/\s*(10|100)\b")


@dataclass
class Alerta:
    cifra: str
    donde: str
    frase: str


def _textos(feedback) -> list[tuple[str, str]]:
    t = [(f"comentario de «{c.nombre}»", c.comentario) for c in feedback.criterios]
    t.append(("fortaleza principal", feedback.fortaleza_principal))
    t += [("cosa a mejorar", x) for x in feedback.tres_cosas_a_mejorar]
    t += [("red flag", x) for x in feedback.red_flags_detectados]
    t.append(("respuesta modelo", feedback.respuesta_modelo))
    if feedback.comparativo_referencia:
        for grupo, items in (("coincidió", feedback.comparativo_referencia.coincide),
                             ("aportó", feedback.comparativo_referencia.aporta),
                             ("le faltó", feedback.comparativo_referencia.le_falto)):
            t += [(f"comparativo ({grupo})", x) for x in items]
    return t


def revisar_feedback(feedback, case: dict) -> list[Alerta]:
    """Cifras del feedback que no aparecen en el caso. Lista vacía = todas salen del contexto o los anexos."""
    caso = texto_del_caso(case)
    alertas: list[Alerta] = []
    vistas: set[str] = set()
    for donde, texto in _textos(feedback):
        for m in _CIFRA.finditer(texto):
            resto = texto[m.end(): m.end() + 6]
            if _PUNTAJE.match(resto):  # "8/10" es un puntaje del propio evaluador, no una cifra del caso
                continue
            valor = float(m.group(1).replace(",", ""))
            if valor in UNIVERSALES or valor <= 12 or 1990 <= valor <= 2100 or m.group(0) in vistas:
                continue  # conteos chicos, años y constantes universales no se contrastan
            inicio = max(0, m.start() - 60)
            frase = texto[inicio: m.end() + 60].strip()
            if not valor_en_contexto(valor, "", caso):
                vistas.add(m.group(0))
                alertas.append(Alerta(m.group(0).strip(), donde, frase))
    return alertas
