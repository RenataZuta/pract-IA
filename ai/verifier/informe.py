"""Guarda el informe (JSON para la app, Markdown para leer) y lo renderiza."""
from __future__ import annotations

from pathlib import Path

from ai.verifier.modelos import Informe

AUDITS_DIR = Path(__file__).resolve().parent.parent / "audits"
ICONO = {"ok": "✅", "discrepancia": "⚠️", "no_evaluable": "➖", "descartado": "🚫",
         "confirmado": "✅", "contradicho": "❌", "no_verificable": "❔"}


def guardar(informe: Informe, carpeta: Path = AUDITS_DIR) -> tuple[Path, Path]:
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta_json, ruta_md = carpeta / f"{informe.caso_id}.json", carpeta / f"{informe.caso_id}.md"
    ruta_json.write_text(informe.model_dump_json(indent=2), encoding="utf-8")
    ruta_md.write_text(a_markdown(informe), encoding="utf-8")
    return ruta_json, ruta_md


def cargar(caso_id: str, carpeta: Path = AUDITS_DIR) -> Informe | None:
    ruta = carpeta / f"{caso_id}.json"
    return Informe.model_validate_json(ruta.read_text(encoding="utf-8")) if ruta.exists() else None


def a_markdown(i: Informe) -> str:
    r = i.resumen
    lineas = [
        f"# Auditoría de {i.caso_id} — {i.titulo}", "",
        f"Generado el {i.generado} con `{i.modelo}`. **Veredicto global: "
        f"{'revisar' if i.veredicto_global == 'revisar' else 'sin hallazgos'}**.", "",
        "| Cuentas ok | Discrepancias | No evaluables | Hechos confirmados | Contradichos | No verificables |",
        "|---|---|---|---|---|---|",
        f"| {r['chequeos_ok']} | {r['discrepancias']} | {r['no_evaluables']} | {r['hechos_confirmados']} | "
        f"{r['hechos_contradichos']} | {r['hechos_no_verificables']} |", "",
        "## Cuentas (calculadas por código)", "",
    ]
    if i.chequeos:
        lineas += ["| | Qué se comprobó | Calculado | Afirmado | Detalle |", "|---|---|---|---|---|"]
        for c in i.chequeos:
            calc = "—" if c.calculado is None else f"{c.calculado:,.4g}"
            afir = "—" if c.afirmado is None else f"{c.afirmado:,.4g}"
            sev = f" ({c.severidad})" if c.severidad else ""
            lineas.append(f"| {ICONO[c.estado]} | {c.descripcion}{sev} | {calc} | {afir} | `{c.formula}` · {c.detalle} |")
    else:
        lineas.append("_Sin cuentas para comprobar._")
    lineas += ["", "## Hechos del mundo real (con fuentes)", ""]
    for h in i.hechos or []:
        lineas += [f"### {ICONO[h.veredicto]} {h.afirmacion}", f"**{h.veredicto}** — {h.resumen}".rstrip(" —")]
        if h.correccion_sugerida:
            lineas.append(f"\n**Corrección sugerida:** {h.correccion_sugerida}")
        for f in h.fuentes:
            sello = "cita verificada" if f.cita_verificada else "cita NO verificada"
            lineas.append(f"- [{f.titulo}]({f.url}) — «{f.cita}» _({sello}, consultada el {h.consultado})_")
        if h.nota:
            lineas.append(f"\n_Nota: {h.nota}_")
        lineas.append("")
    if not i.hechos:
        lineas.append("_No se verificaron hechos del mundo real en esta corrida._\n")
    if i.descartados:
        lineas += ["## Propuestas del modelo descartadas por el código", ""] + [f"- {d}" for d in i.descartados] + [""]
    lineas += ["## Límites de esta auditoría", ""] + [f"- {x}" for x in i.limitaciones]
    return "\n".join(lineas) + "\n"
