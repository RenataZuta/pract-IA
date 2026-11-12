"""Lee las tablas markdown de los anexos de un caso y las convierte en celdas numéricas."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

_MONEDAS = re.compile(r"S/|USD|US\$|PEN|\$")
_RANGO = re.compile(r"\d\s*[-–]\s*\d")
_SEPARADOR = re.compile(r"^\|?[\s:|-]+\|?$")
_MULTIPLICADOR = {"k": 1e3, "m": 1e6}


class ErrorCelda(ValueError):
    """La fila, la columna o el número que pidió el modelo no existe o no es único."""


def _clave(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.replace("**", "").replace("*", "").replace("\\", "")
    return re.sub(r"\s+", " ", t).strip().lower().rstrip(":")


def a_numero(celda: str) -> float | None:
    """'8,400' -> 8400; '(6,300)' -> -6300; 'S/ 320K' -> 320000; '24%' -> 24; texto o rango -> None."""
    s = celda.replace("**", "").replace("*", "").strip()
    if not s or _RANGO.search(s):
        return None
    m = re.search(r"\d[\d,]*(?:\.\d+)?", s)
    if not m:
        return None
    prefijo = _MONEDAS.sub("", s[: m.start()])
    if re.search(r"[A-Za-zÁ-ú]{2,}", prefijo):  # hay texto antes del número: no es una celda numérica
        return None
    valor = float(m.group().replace(",", ""))
    resto = re.match(r"([kKmM])(?![\wÀ-ú²])", s[m.end():])
    if resto:
        valor *= _MULTIPLICADOR[resto.group(1).lower()]
    negativo = s.startswith("(") or s.startswith(("-", "−", "–"))
    return -valor if negativo else valor


@dataclass
class Tabla:
    indice: int  # T1, T2... en el orden del caso
    anexo: int
    titulo: str
    columnas: list[str]
    filas: list[list[str]]

    def _buscar(self, pedido: str, candidatos: list[str], que: str) -> int:
        k = _clave(pedido)
        claves = [_clave(c) for c in candidatos]
        for criterio in (lambda c: c == k, lambda c: c.startswith(k), lambda c: k in c):
            hallados = [i for i, c in enumerate(claves) if c and criterio(c)]
            if len(hallados) == 1:
                return hallados[0]
            if len(hallados) > 1:
                raise ErrorCelda(f"T{self.indice}: {que} '{pedido}' es ambigua")
        raise ErrorCelda(f"T{self.indice}: no existe {que} '{pedido}'")

    def valor(self, fila: str, columna: str) -> float:
        f = self._buscar(fila, [r[0] for r in self.filas], "la fila")
        c = self._buscar(columna, self.columnas[1:], "la columna") + 1
        celda = self.filas[f][c] if c < len(self.filas[f]) else ""
        numero = a_numero(celda)
        if numero is None:
            raise ErrorCelda(f"T{self.indice}: la celda ({fila}, {columna}) no es numérica: '{celda.strip()}'")
        return numero


def _celdas(linea: str) -> list[str]:
    partes = linea.strip().strip("|").split("|")
    return [p.strip() for p in partes]


def parsear_tablas(case: dict) -> list[Tabla]:
    """Todas las tablas markdown de los anexos, numeradas T1, T2... en orden."""
    tablas: list[Tabla] = []
    for n_anexo, anexo in enumerate(case.get("exhibits") or [], 1):
        bloque: list[str] = []
        for linea in anexo["content"].splitlines() + [""]:
            if linea.strip().startswith("|"):
                bloque.append(linea)
                continue
            if len(bloque) >= 3 and _SEPARADOR.match(bloque[1].replace(" ", "")):
                columnas = _celdas(bloque[0])
                if not columnas[0]:
                    columnas[0] = "fila"
                filas = [_celdas(f) for f in bloque[2:]]
                tablas.append(Tabla(len(tablas) + 1, n_anexo, anexo["title"], columnas, filas))
            bloque = []
    return tablas


def describir(tablas: list[Tabla]) -> str:
    """Las tablas en texto compacto para el prompt: el modelo ve los mismos rótulos que usará el código."""
    partes = []
    for t in tablas:
        filas = "\n".join(" | ".join(c.replace("**", "") for c in f) for f in t.filas)
        partes.append(f"T{t.indice} (Anexo {t.anexo}: {t.titulo})\ncolumnas: {' | '.join(t.columnas)}\n{filas}")
    return "\n\n".join(partes)
