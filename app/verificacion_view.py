"""
Ficha de verificación de un caso (solo lectura).

Muestra lo que el agente verificador (`ai/verifier/`) comprobó de ese caso y con qué fuentes. Lee el informe ya
guardado en `ai/audits/<id>.json`: no llama a ningún modelo ni gasta tokens. Si el caso no tiene informe, no pinta nada.
"""
from __future__ import annotations

import streamlit as st
from loguru import logger

ICONO = {"ok": "✅", "discrepancia": "⚠️", "confirmado": "✅", "contradicho": "❌", "no_verificable": "❔"}


def _enlace(titulo: str, url: str) -> str:
    """Markdown de un enlace; solo http(s) (el informe lo escribió un modelo, no se confía en el esquema)."""
    titulo = titulo.replace("[", "(").replace("]", ")")
    return f"[{titulo}]({url})" if url.startswith(("http://", "https://")) else titulo


def render(case_id: str) -> None:
    """Pinta la ficha de `case_id` si existe; nunca rompe la vista del caso."""
    try:
        from ai.verifier.informe import cargar

        informe = cargar(case_id)
    except Exception as exc:  # la ficha es un extra: cualquier problema se registra y se omite
        logger.warning("No se pudo leer la verificación de {}: {}", case_id, exc)
        return
    if informe is None:
        return

    r = informe.resumen
    estado = "✅ sin discrepancias" if informe.veredicto_global == "sin_hallazgos" else "⚠️ con observaciones por revisar"
    if r["hechos_no_verificables"]:
        estado += f" · {r['hechos_no_verificables']} hecho(s) sin verificar"
    with st.expander(f"🔎 Verificación del caso por el agente · {estado}"):
        st.caption(
            f"Auditado el {informe.generado}. El agente **propone** y una persona decide. Las cifras de los anexos son "
            "sintéticas: se comprueba su coherencia interna y los hechos del mundo real con fuentes."
        )
        a, b, c, d = st.columns(4)
        a.metric("Cuentas ok", r["chequeos_ok"])
        b.metric("Discrepancias", r["discrepancias"])
        c.metric("Hechos confirmados", r["hechos_confirmados"])
        d.metric("No verificables", r["hechos_no_verificables"])

        if informe.hechos:
            st.markdown("**Hechos del mundo real**")
            for h in informe.hechos:
                st.markdown(f"{ICONO[h.veredicto]} **{h.afirmacion}** — _{h.veredicto}_. {h.resumen}")
                if h.correccion_sugerida:
                    st.markdown(f"Corrección sugerida: {h.correccion_sugerida}")
                for f in h.fuentes:
                    sello = "cita verificada en la página" if f.cita_verificada else "cita sin verificar"
                    st.markdown(f"- {_enlace(f.titulo, f.url)} — «{f.cita}» _({sello}; consultada el {h.consultado})_")
                if h.nota:
                    st.caption(h.nota)

        revisables = [x for x in informe.chequeos if x.estado in ("ok", "discrepancia")]
        if revisables:
            st.markdown("**Cuentas calculadas por código**")
            for x in revisables:
                detalle = "" if x.estado == "ok" else f" (calculado {x.calculado:,.4g}, afirmado {x.afirmado:,.4g})"
                st.markdown(f"- {ICONO[x.estado]} {x.descripcion}{detalle}")
        st.caption("Límites: " + " ".join(informe.limitaciones[:3]))
