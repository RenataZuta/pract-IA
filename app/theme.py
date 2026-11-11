"""
Identidad visual por empresa, industria y modo.

Cada caso se ve con los colores de su empresa: una franja con monograma (no logos
reales, que tienen derechos de marca), chips con tipo de caso, duración y anexos, y
la tarjeta de misión. Los colores son "inspirados" en cada marca y están elegidos
para que el texto blanco sobre el fondo oscuro cumpla contraste WCAG AA (4.5:1).

Solo genera HTML/CSS; no toca st.session_state ni llama a Streamlit.
"""
from __future__ import annotations

from dataclasses import dataclass
from html import escape


@dataclass(frozen=True)
class Tema:
    nombre: str
    acento: str  # color de marca (detalles, barras, botón)
    oscuro: str  # fondo oscuro de la franja; el texto blanco debe leerse sobre él
    monograma: str


INDUSTRIAS = {  # color por defecto, icono y lema por industria
    "Banca": (Tema("Banca", "#2B6CB0", "#0B2545", "BCA"), "🏦", "Decide con ratios, riesgo y criterio."),
    "FMCG": (Tema("FMCG", "#DD6B20", "#5A2A0B", "FMCG"), "🛒", "Entiende al consumidor y al canal peruano."),
    "Consultoría": (Tema("Consultoría", "#2F855A", "#0F3D2A", "CON"), "🧭", "Hipótesis primero, datos después."),
}
ENTREVISTA = Tema("Entrevista", "#6B46C1", "#2D1A5E", "1:1")

# Clave en minúsculas buscada dentro de case["company"].
EMPRESAS = {
    "bcp": Tema("BCP", "#FF7800", "#0A2A6B", "BCP"),
    "interbank": Tema("Interbank", "#00A94F", "#0B5A31", "IBK"),
    "scotiabank": Tema("Scotiabank", "#EC111A", "#7A0A10", "SCO"),
    "credicorp": Tema("Credicorp Capital", "#3B82C4", "#0B2545", "CCAP"),
    "alicorp": Tema("Alicorp", "#D7282F", "#5C0F14", "ALI"),
    "belcorp": Tema("Belcorp", "#C2185B", "#5B0A2B", "BEL"),
    "backus": Tema("Backus", "#D4A017", "#6B0F1A", "BKS"),
    "nestl": Tema("Nestlé", "#C8102E", "#4A2C1A", "NES"),
    "apoyo": Tema("Apoyo Consultoría", "#00A3AD", "#04444A", "APY"),
    "lima consulting": Tema("Lima Consulting", "#8E44AD", "#3B1A4F", "LCG"),
    "deloitte": Tema("Deloitte", "#86BC25", "#1F3A0A", "DEL"),
}


def tema_de(case: dict) -> Tema:
    """Tema de la empresa del caso; si no hay uno propio, el de su industria."""
    empresa = case.get("company", "").lower()
    for clave, tema in EMPRESAS.items():
        if clave in empresa:
            return tema
    return INDUSTRIAS.get(case.get("industry", ""), INDUSTRIAS["Banca"])[0]


def icono_y_lema(industria: str) -> tuple[str, str]:
    _, icono, lema = INDUSTRIAS.get(industria, INDUSTRIAS["Banca"])
    return icono, lema


# ---------- contraste (WCAG) ----------
def luminancia(hex_color: str) -> float:
    r, g, b = (int(hex_color.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4))
    lineal = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in (r, g, b)]
    return 0.2126 * lineal[0] + 0.7152 * lineal[1] + 0.0722 * lineal[2]


def contraste(a: str, b: str) -> float:
    la, lb = sorted((luminancia(a), luminancia(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def texto_sobre(fondo: str) -> str:
    """Blanco o casi negro, el que mejor contraste dé sobre `fondo`."""
    return "#FFFFFF" if contraste("#FFFFFF", fondo) >= contraste("#111111", fondo) else "#111111"


# ---------- piezas HTML/CSS ----------
def css(tema: Tema) -> str:
    """Estilos de la página con el color de la empresa (se inyectan con unsafe_allow_html)."""
    return f"""
<style>
section[data-testid="stSidebar"] {{ border-top: 4px solid {tema.acento}; }}
button[data-testid="stBaseButton-primary"] {{ background-color: {tema.acento}; border-color: {tema.acento}; color: {texto_sobre(tema.acento)}; }}
button[data-testid="stBaseButton-primary"]:hover {{ filter: brightness(0.92); border-color: {tema.acento}; color: {texto_sobre(tema.acento)}; }}
/* la barra de Streamlit anida 3 capas; la del relleno es la más profunda */
div[data-testid="stProgress"] [role="progressbar"] > div > div > div {{ background-color: {tema.acento}; }}
.px-banda {{ display:flex; align-items:center; gap:14px; padding:14px 18px; border-radius:14px; margin:0 0 14px 0;
  background:linear-gradient(135deg, {tema.oscuro}, {tema.oscuro}F2 60%, {tema.acento}55); color:#FFFFFF; border-left:6px solid {tema.acento}; }}
.px-mono {{ min-width:54px; height:54px; padding:0 6px; border-radius:50%; display:flex; align-items:center; justify-content:center;
  background:{tema.acento}; color:{texto_sobre(tema.acento)}; font-weight:800; font-size:15px; letter-spacing:.5px; }}
.px-kicker {{ font-size:13px; opacity:.85; margin-bottom:6px; }}
.px-chip {{ display:inline-block; margin:0 6px 4px 0; padding:3px 10px; border-radius:999px; font-size:12px;
  background:rgba(255,255,255,.14); border:1px solid rgba(255,255,255,.35); color:#FFFFFF; }}
.px-mision {{ border-left:6px solid {tema.acento}; background:{tema.acento}14; border-radius:10px; padding:14px 18px; margin:6px 0 4px 0; }}
.px-mision b {{ color:{tema.acento}; }}
.px-tag {{ display:inline-block; margin:4px 6px 0 0; padding:2px 10px; border-radius:999px; font-size:12px; border:1px solid {tema.acento}; color:{tema.acento}; }}
.px-pasos {{ display:flex; gap:8px; margin:0 0 10px 0; flex-wrap:wrap; }}
.px-paso {{ flex:1; min-width:120px; padding:6px 10px; border-radius:10px; font-size:13px; border:1px solid rgba(128,128,128,.35); opacity:.6; }}
.px-paso.hecho {{ opacity:1; border-color:{tema.acento}; }}
.px-paso.actual {{ opacity:1; background:{tema.acento}; color:{texto_sobre(tema.acento)}; border-color:{tema.acento}; font-weight:700; }}
</style>
"""


def banda_html(case: dict, tema: Tema, icono: str) -> str:
    n_anexos = len(case.get("exhibits") or [])
    chips = [case["case_type"], f"⏱ {case['duration_minutes']} min", f"📎 {n_anexos} anexo{'s' if n_anexos != 1 else ''}"]
    return (
        f'<div class="px-banda" role="banner" aria-label="Empresa: {escape(case["company"])}">'
        f'<div class="px-mono">{escape(tema.monograma)}</div>'
        f'<div><div class="px-kicker">{icono} {escape(case["company"])} · {escape(case["industry"])}</div>'
        + "".join(f'<span class="px-chip">{escape(c)}</span>' for c in chips)
        + "</div></div>"
    )


def banda_generica(kicker: str, chips: list[str], tema: Tema) -> str:
    """Franja para pantallas sin caso (modo entrevista)."""
    return (
        f'<div class="px-banda"><div class="px-mono">{escape(tema.monograma)}</div>'
        f'<div><div class="px-kicker">{escape(kicker)}</div>'
        + "".join(f'<span class="px-chip">{escape(c)}</span>' for c in chips)
        + "</div></div>"
    )


def mision_html(case: dict, lema: str) -> str:
    temas = "".join(f'<span class="px-tag">{escape(t)}</span>' for t in case.get("temas_evaluados", []))
    return (
        f'<div class="px-mision"><b>Tu misión</b><br>{escape(case["prompt"])}'
        f'<div style="margin-top:8px;font-size:13px;opacity:.85">Se evalúa: </div>{temas}'
        f'<div style="margin-top:8px;font-size:12px;opacity:.7"><i>{escape(lema)}</i></div></div>'
    )


PASOS = ("1 · Leer el caso", "2 · Responder", "3 · Evaluar", "4 · Guion final")


def pasos_html(actual: int) -> str:
    """Recorrido guiado; `actual` va de 1 a 4 (5 = todo hecho)."""
    items = []
    for i, nombre in enumerate(PASOS, 1):
        estado = "actual" if i == actual else "hecho" if i < actual else ""
        marca = "✓ " if i < actual else ""
        items.append(f'<div class="px-paso {estado}">{marca}{escape(nombre)}</div>')
    return f'<div class="px-pasos" role="list">{"".join(items)}</div>'
