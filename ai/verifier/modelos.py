"""Modelos (Pydantic) de lo que el agente extrae, comprueba y reporta."""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

TIPOS_HECHO = ("propiedad_marca", "fecha_evento", "existencia", "cifra_mercado", "otro")


def _numero(valor):
    """Acepta '4,000,000' o '37%' donde se pide un número; None si no se puede leer."""
    if isinstance(valor, str):
        from ai.verifier.tablas import a_numero
        return a_numero(valor)
    return valor


def _entero(valor):
    """Los LLM a veces devuelven 1.0 o '1' donde se pide un entero."""
    if isinstance(valor, float):
        return int(round(valor))
    return int(valor) if isinstance(valor, str) and valor.strip().isdigit() else valor


# ---------- Lo que el LLM propone (todavía sin comprobar) ----------
class Variable(BaseModel):
    """Una celda de tabla (tabla, fila, columna) o una constante con su cita textual."""

    tabla: int | None = None
    fila: str | None = None
    columna: str | None = None
    valor: float | None = None
    cita: str | None = None

    @field_validator("valor", mode="before")
    @classmethod
    def _valor(cls, v):
        return _numero(v)

    @field_validator("tabla", mode="before")
    @classmethod
    def _tabla(cls, v):
        if isinstance(v, str):  # "T2" -> 2
            m = re.search(r"\d+", v)
            return int(m.group()) if m else None
        return _entero(v)

    @model_validator(mode="after")
    def _una_forma(self):
        es_celda = self.tabla is not None and bool(self.fila) and bool(self.columna)
        es_constante = self.valor is not None and bool(self.cita)
        if not (es_celda or es_constante):
            raise ValueError("una variable es una celda (tabla, fila, columna) o una constante (valor, cita)")
        return self


class Afirmado(BaseModel):
    """Lo que el caso afirma: un número con su cita, o una expresión (identidad entre celdas)."""

    valor: float | None = None
    cita: str | None = None
    decimales: int = Field(default=0, ge=0, le=4)
    expresion: str | None = None

    @field_validator("valor", mode="before")
    @classmethod
    def _valor(cls, v):
        return _numero(v)

    @field_validator("decimales", mode="before")
    @classmethod
    def _decimales(cls, v):
        return _entero(v)

    @model_validator(mode="after")
    def _una_forma(self):
        if not (self.expresion or (self.valor is not None and self.cita)):
            raise ValueError("lo afirmado necesita (valor y cita) o una expresión")
        return self


class ChequeoNumerico(BaseModel):
    id: str
    descripcion: str = Field(max_length=300)
    variables: dict[str, Variable]
    calculo: str
    afirmado: Afirmado


class HechoReal(BaseModel):
    id: str
    afirmacion: str = Field(max_length=300)
    tipo: Literal["propiedad_marca", "fecha_evento", "existencia", "cifra_mercado", "otro"] = "otro"
    cita_caso: str = ""

    @field_validator("tipo", mode="before")
    @classmethod
    def _tipo(cls, v):
        return v if v in TIPOS_HECHO else "otro"


# ---------- Lo que el sistema comprueba y reporta ----------
class ResultadoChequeo(BaseModel):
    id: str
    descripcion: str
    formula: str = ""
    estado: Literal["ok", "discrepancia", "no_evaluable", "descartado"]
    calculado: float | None = None
    afirmado: float | None = None
    diferencia_relativa: float | None = None
    severidad: Literal["alta", "media", "baja"] | None = None
    detalle: str = ""


class Fuente(BaseModel):
    titulo: str
    url: str
    cita: str
    cita_verificada: bool  # la cita se encontró en el texto de la página que el agente abrió


class RespuestaHecho(BaseModel):
    """Lo que devuelve el LLM tras buscar; todavía pasa por los guardarraíles."""

    veredicto: Literal["confirmado", "contradicho", "no_verificable"]
    resumen: str = ""
    correccion_sugerida: str | None = None
    fuentes: list[dict] = Field(default_factory=list)


class VeredictoHecho(BaseModel):
    id: str
    afirmacion: str
    tipo: str = "otro"
    veredicto: Literal["confirmado", "contradicho", "no_verificable"]
    resumen: str = ""
    correccion_sugerida: str | None = None
    fuentes: list[Fuente] = Field(default_factory=list)
    busquedas: list[str] = Field(default_factory=list)
    paginas_abiertas: list[str] = Field(default_factory=list)
    consultado: str = ""
    nota: str = ""  # por qué se degradó a no_verificable, si pasó


class Informe(BaseModel):
    caso_id: str
    titulo: str
    generado: str
    modelo: str
    veredicto_global: Literal["sin_hallazgos", "revisar"]
    resumen: dict[str, int]
    chequeos: list[ResultadoChequeo]
    hechos: list[VeredictoHecho]
    descartados: list[str] = Field(default_factory=list)  # propuestas del modelo que no pasaron la validación
    limitaciones: list[str] = Field(default_factory=list)
