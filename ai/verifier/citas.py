"""Comparación de citas textuales: la base del "sin fuente no hay veredicto"."""
from __future__ import annotations

import re
from difflib import SequenceMatcher

_MARCAS = re.compile(r"\*\*|\*|\\|\||`")
_PREFIJO_LINEA = re.compile(r"^L\d+:\s?", re.M)  # el navegador de Groq numera las líneas "L12: texto"


def normalizar(texto: str) -> str:
    """Minúsculas, sin marcas markdown ni barras de tabla y con espacios colapsados."""
    t = _PREFIJO_LINEA.sub("", texto)
    t = _MARCAS.sub(" ", t).replace(" ", " ").replace("’", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", t).strip().lower()


_ELIPSIS = re.compile(r"\s*(?:…|\.{3}|\[\.{2,3}\])\s*")


def _fragmento_en_texto(c: str, t: str, umbral: float) -> bool:
    if c in t:
        return True
    coincidencia = SequenceMatcher(None, t, c, autojunk=False).find_longest_match(0, len(t), 0, len(c))
    return coincidencia.size >= umbral * len(c)


def cita_en_texto(cita: str, texto: str, umbral: float = 0.9) -> bool:
    """True si la cita está en el texto, igual o casi igual (ignora marcas, espacios y mayúsculas).

    Busca la cita exacta; si no, acepta una coincidencia contigua que cubra al menos `umbral` de la
    cita (tolera un guion o una coma distintos, no una paráfrasis). Una cita con «…» se verifica
    fragmento por fragmento: todos los fragmentos de 12+ caracteres deben estar en el texto.
    """
    t = normalizar(texto)
    fragmentos = [normalizar(f) for f in _ELIPSIS.split(cita)]
    fragmentos = [f for f in fragmentos if len(f) >= 12] or [normalizar(cita)]
    if sum(len(f) for f in fragmentos) < 8:  # una cita tan corta no demuestra nada
        return False
    return all(_fragmento_en_texto(f, t, umbral) for f in fragmentos)


def _escrituras(valor: float) -> set[str]:
    entero = abs(valor) == int(abs(valor))
    base = f"{abs(valor):.0f}" if entero else f"{abs(valor):g}"
    return {base, base.replace(".", ",")} | ({f"{int(abs(valor)):,}"} if entero else set())


UNIVERSALES = {12, 30, 52, 60, 100, 360, 365, 1000}  # meses, días, semanas, %, miles: no están "en el caso"
_PALABRA_CLAVE = re.compile(r"[a-záéíóúñü]{4,}")
VENTANA = 200


def valor_en_contexto(valor: float, cita: str, texto: str, umbral: float = 0.6) -> bool:
    """True si el número aparece en el texto junto a las palabras clave de la cita.

    Tolera citas parafraseadas, pero no números inventados: el número (tal cual o con otra escala) tiene
    que existir en el texto y, a ±200 caracteres, deben estar al menos `umbral` de las palabras de la cita.
    """
    t = normalizar(texto)
    palabras = set(_PALABRA_CLAVE.findall(normalizar(cita)))
    for escala in (1, 1e3, 1e6, 1e9, 1e-2):
        for x in _escrituras(round(valor / escala, 9)):
            ceros = "0*" if re.search(r"[.,]", x) else ""  # 1.4 también se escribe 1.40
            for m in re.finditer(rf"(?<![\d.,]){re.escape(x)}{ceros}(?![\d])", t):
                if not palabras:
                    return True
                ventana = set(_PALABRA_CLAVE.findall(t[max(0, m.start() - VENTANA): m.end() + VENTANA]))
                if len(palabras & ventana) >= umbral * len(palabras):
                    return True
    return False


_PALABRAS = {"un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7,
             "ocho": 8, "nueve": 9, "diez": 10, "once": 11, "doce": 12}


def numero_en_cita(valor: float, cita: str) -> bool:
    """True si el número aparece escrito en la cita, tal cual o con otra escala.

    Acepta separador de miles y conversiones de unidades que el modelo hace al leer
    ("4 millones" -> 4000000, "37%" -> 0.37): los dígitos tienen que seguir estando en la cita.
    """
    c = normalizar(cita)
    if any(n == abs(valor) and re.search(rf"\b{w}\b", c) for w, n in _PALABRAS.items()):
        return True
    sin_comas = c.replace(",", "")
    for escala in (1, 1e3, 1e6, 1e9, 1e-2):
        if any(x in c or x.replace(",", "") in sin_comas for x in _escrituras(round(valor / escala, 9))):
            return True
    return False
