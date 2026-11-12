"""
Las cuentas las hace el código, nunca el modelo.

El LLM propone *qué* comparar (celdas de las tablas + una fórmula); este módulo resuelve
las celdas, evalúa la fórmula con un intérprete aritmético seguro (sin `eval`) y compara
con lo que el caso afirma. Si el modelo inventa una cita o una celda, el chequeo se descarta.
"""
from __future__ import annotations

import ast
import operator
import re

from ai.verifier.citas import UNIVERSALES, cita_en_texto, valor_en_contexto
from ai.verifier.modelos import ChequeoNumerico, ResultadoChequeo, Variable
from ai.verifier.tablas import ErrorCelda, Tabla

_BINARIOS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow,
}
_UNARIOS = {ast.USub: operator.neg, ast.UAdd: operator.pos}
_FUNCIONES = {"abs": abs, "min": min, "max": max, "round": round}
_MAX_LARGO = 200
_MAX_NODOS = 60


class ErrorExpresion(ValueError):
    """La fórmula no es aritmética simple, usa algo no permitido o no se puede evaluar."""


def evaluar(expresion: str, variables: dict[str, float]) -> float:
    """Evalúa una fórmula con + - * / ** ( ), abs/min/max/round y las variables dadas."""
    if len(expresion) > _MAX_LARGO:
        raise ErrorExpresion("la fórmula es demasiado larga")
    try:
        arbol = ast.parse(expresion.strip(), mode="eval")
    except SyntaxError as exc:
        raise ErrorExpresion(f"fórmula inválida: {exc.msg}") from exc
    if sum(1 for _ in ast.walk(arbol)) > _MAX_NODOS:
        raise ErrorExpresion("la fórmula es demasiado compleja")
    try:
        resultado = _nodo(arbol.body, variables)
    except ZeroDivisionError as exc:
        raise ErrorExpresion("división entre cero") from exc
    except OverflowError as exc:
        raise ErrorExpresion("el resultado es demasiado grande") from exc
    return float(resultado)


def _nodo(n: ast.AST, variables: dict[str, float]) -> float:
    if isinstance(n, ast.Constant) and type(n.value) in (int, float):
        return n.value
    if isinstance(n, ast.Name):
        if n.id not in variables:
            raise ErrorExpresion(f"variable desconocida: {n.id}")
        return variables[n.id]
    if isinstance(n, ast.BinOp) and type(n.op) in _BINARIOS:
        izq, der = _nodo(n.left, variables), _nodo(n.right, variables)
        if isinstance(n.op, ast.Pow) and (abs(der) > 6 or abs(izq) > 1e6):
            raise ErrorExpresion("potencia fuera de rango")
        return _BINARIOS[type(n.op)](izq, der)
    if isinstance(n, ast.UnaryOp) and type(n.op) in _UNARIOS:
        return _UNARIOS[type(n.op)](_nodo(n.operand, variables))
    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in _FUNCIONES and not n.keywords:
        if not 1 <= len(n.args) <= 4:
            raise ErrorExpresion("número de argumentos no permitido")
        return _FUNCIONES[n.func.id](*[_nodo(a, variables) for a in n.args])
    raise ErrorExpresion(f"elemento no permitido en la fórmula: {type(n).__name__}")


def _escala_escrita(cita: str, valor: float) -> float:
    """"S/ 3M" o "3 millones" se escriben con 0 decimales en millones: la precisión es ±0.5M, no ±0.5 soles."""
    c = (cita or "").lower()
    if abs(valor) >= 1e5 and re.search(r"millon|\d\s*m\b", c):
        return 1e6
    if abs(valor) >= 100 and re.search(r"\bmil\b|\d\s*k\b", c):
        return 1e3
    return 1.0


def _severidad(diferencia_relativa: float) -> str:
    return "alta" if diferencia_relativa >= 0.20 else "media" if diferencia_relativa >= 0.05 else "baja"


def _resolver(v: Variable, tablas: list[Tabla]) -> float:
    if v.valor is not None and v.cita:
        return v.valor
    tabla = next((t for t in tablas if t.indice == v.tabla), None)
    if tabla is None:
        raise ErrorCelda(f"no existe la tabla T{v.tabla}")
    return tabla.valor(v.fila or "", v.columna or "")


def _diferencia_de_unidades(calculado: float, afirmado: float) -> bool:
    """¿Se parecen salvo por un factor 100, 1.000 o 1.000.000? (típico: % vs fracción, miles vs unidades)."""
    if calculado == 0 or afirmado == 0:
        return False
    r = abs(calculado / afirmado)
    return any(abs(r / f - 1) < 0.03 or abs(r * f - 1) < 0.03 for f in (100, 1e3, 1e6))  # 3%: tolera redondeos


def evaluar_chequeo(ch: ChequeoNumerico, tablas: list[Tabla], texto_caso: str,
                    texto_afirmaciones: str | None = None) -> ResultadoChequeo:
    """Resuelve celdas, calcula y compara. Estados: ok, discrepancia, no_evaluable, descartado.

    `texto_caso` es todo el caso; `texto_afirmaciones` es solo lo que *afirma* (contexto, pregunta, pista y
    referencia, sin los anexos): sirve para descartar «lecturas» que comparan una celda con el mismo anexo.
    """
    base = {"id": ch.id, "descripcion": ch.descripcion, "formula": ch.calculo}

    def sin_resultado(estado: str, detalle: str) -> ResultadoChequeo:
        return ResultadoChequeo(**base, estado=estado, detalle=detalle)

    # Guardarraíl 0: un chequeo que solo copia una constante compara el número consigo mismo; no comprueba nada.
    unica = ch.calculo.strip()
    if unica in ch.variables and ch.variables[unica].cita is not None:
        return sin_resultado("descartado", "chequeo trivial: solo copia un número del caso, no lo contrasta con nada")

    # Guardarraíl 1: ningún número puede ser inventado. Debe estar en el caso junto a las palabras de su cita
    # (las constantes universales, como 12 meses o 100 %, no tienen que estar).
    citas = [(f"la variable '{n}'", v.valor, v.cita) for n, v in ch.variables.items() if v.cita]
    if ch.afirmado.cita:
        citas.append(("lo afirmado", ch.afirmado.valor, ch.afirmado.cita))
    for donde, valor, cita in citas:
        if valor is not None:
            if abs(valor) not in UNIVERSALES and not valor_en_contexto(valor, cita, texto_caso):
                return sin_resultado("descartado", f"el número {valor:g} de {donde} no aparece en el caso junto a «{cita}»")
        elif not cita_en_texto(cita, texto_caso):
            return sin_resultado("descartado", f"la cita de {donde} no aparece en el caso: «{cita}»")

    # Guardarraíl 1b: leer una celda y compararla con una cita que sale de ese mismo anexo no comprueba nada.
    if (unica in ch.variables and ch.variables[unica].cita is None and ch.afirmado.cita
            and ch.afirmado.valor is not None and texto_afirmaciones is not None
            and not valor_en_contexto(ch.afirmado.valor, ch.afirmado.cita, texto_afirmaciones)):
        return sin_resultado("descartado", "lectura de una celda: lo afirmado sale del mismo anexo, no comprueba nada")

    try:
        valores = {n: _resolver(v, tablas) for n, v in ch.variables.items()}
        calculado = evaluar(ch.calculo, valores)
        if ch.afirmado.expresion:
            afirmado = evaluar(ch.afirmado.expresion, valores)
            tolerancia = max(0.005 * max(abs(calculado), abs(afirmado)), 0.05)
        else:
            afirmado = float(ch.afirmado.valor)  # type: ignore[arg-type]
            tolerancia = 0.5 * 10 ** (-ch.afirmado.decimales) * _escala_escrita(ch.afirmado.cita or "", afirmado) * 1.001 + 1e-9
            if any(m in (ch.afirmado.cita or "").lower() for m in ("~", "aprox", "cerca de", "unos ", "alrededor")):
                tolerancia = max(tolerancia, 0.03 * abs(afirmado))
    except (ErrorCelda, ErrorExpresion) as exc:
        return sin_resultado("no_evaluable", str(exc))

    detalle = ", ".join(f"{n}={v:g}" for n, v in valores.items())
    if not ch.afirmado.expresion and calculado * afirmado < 0:
        # Los gastos van entre paréntesis (negativos) pero el texto habla de magnitudes: se compara sin signo.
        calculado, afirmado = abs(calculado), abs(afirmado)
        detalle += " (signo opuesto ignorado)"
    if _diferencia_de_unidades(calculado, afirmado):
        return sin_resultado("no_evaluable", f"parece una diferencia de unidades ({calculado:g} vs {afirmado:g}); {detalle}")
    diferencia = abs(calculado - afirmado)
    relativa = diferencia / max(abs(afirmado), abs(calculado), 1e-9)
    ok = diferencia <= tolerancia
    return ResultadoChequeo(
        **base, estado="ok" if ok else "discrepancia", calculado=calculado, afirmado=afirmado,
        diferencia_relativa=None if ok else relativa, severidad=None if ok else _severidad(relativa),
        detalle=detalle,
    )
