"""
Exporta el feedback del evaluador a PDF con reportlab.

Solo arma el documento; la UI (app/main.py) lo ofrece con st.download_button.
"""
from __future__ import annotations

import unicodedata
from datetime import date
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ai.evaluator import Feedback
from ai.guion import GuionFinal, hhmmss

TIPO_TITULOS = {"tecnico": "Técnico", "blando": "Habilidades blandas", "innovacion": "Aporte propio"}

# Helvetica solo cubre cp1252. Los LLM escriben espacios y guiones "no separables"
# (U+202F, U+2011...) que saldrían como "?": NFKC los normaliza, se reemplazan los
# símbolos más comunes y lo demás se degrada a "?" en vez de romper el PDF.
_REEMPLAZOS = {
    "→": "->", "←": "<-", "−": "-", "≥": ">=", "≤": "<=", "≈": "~",
    "\u2010": "-", "\u2011": "-", "\u2012": "-", "\u00ad": "", "\u200b": "",
}


def _safe(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    for original, reemplazo in _REEMPLAZOS.items():
        text = text.replace(original, reemplazo)
    return text.encode("cp1252", errors="replace").decode("cp1252")


def _para(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(_safe(text)).replace("\n", "<br/>"), style)


def feedback_to_pdf(feedback: Feedback, case: dict, transcript: str) -> bytes:
    """Devuelve el PDF del feedback como bytes."""
    base = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=base["BodyText"], fontSize=10, leading=14)
    small = ParagraphStyle("small", parent=body, fontSize=9, leading=12)
    h2 = ParagraphStyle("h2", parent=base["Heading2"], spaceBefore=14, spaceAfter=4)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="PractIA — Feedback de group case",
        author="PractIA",
    )

    story: list = [
        _para("PractIA — Feedback de group case", base["Title"]),
        _para(
            f"{case['company']} · {case['title']} "
            f"({case['industry']} · {case['case_type']})",
            body,
        ),
        _para(f"Generado el {date.today():%d/%m/%Y}", small),
        Spacer(1, 10),
        _para(f"Puntaje total: {feedback.puntaje_total}/100", base["Heading1"]),
    ]
    if feedback.puntaje_por_tipo:
        partes = [f"{TIPO_TITULOS.get(t, t)} {p}/100" for t, p in feedback.puntaje_por_tipo.items()]
        story.append(_para(" · ".join(partes), body))

    # Criterios: tabla con el comentario ajustado a la columna.
    filas = [[_para("Criterio", small), _para("Puntaje", small), _para("Comentario", small)]]
    for criterio in feedback.criterios:
        filas.append([
            _para(criterio.nombre + (f" ({criterio.peso * 100:.0f} %)" if criterio.peso else ""), small),
            _para(f"{criterio.puntaje}/10", small),
            _para(criterio.comentario, small),
        ])
    tabla = Table(filas, colWidths=[4.5 * cm, 1.8 * cm, 10.7 * cm], repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef5")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b8c2cc")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story += [Spacer(1, 4), tabla]

    comparativo = feedback.comparativo_referencia
    if comparativo:
        story.append(_para("Comparativo con la respuesta de referencia", h2))
        for titulo, items in (("Coincidiste en", comparativo.coincide), ("Aportaste", comparativo.aporta),
                              ("Te faltó", comparativo.le_falto)):
            story.append(_para(f"{titulo}: " + ("; ".join(items) or "—"), body))

    story += [
        _para("Fortaleza principal", h2),
        _para(feedback.fortaleza_principal, body),
        _para("Tres cosas a mejorar", h2),
        *[_para(f"• {item}", body) for item in feedback.tres_cosas_a_mejorar],
    ]
    if feedback.red_flags_detectados:
        story += [
            _para("Red flags detectados", h2),
            *[_para(f"• {item}", body) for item in feedback.red_flags_detectados],
        ]
    story += [
        _para("Respuesta modelo", h2),
        _para(feedback.respuesta_modelo, body),
        _para("Tu transcripción", h2),
        _para(transcript, small),
    ]

    doc.build(story)
    return buffer.getvalue()


def guion_to_pdf(guion: GuionFinal, case: dict, feedback: Feedback, transcript: str) -> bytes:
    """Un solo PDF para practicar: guion final, qué cambió, contraste con la referencia y tu respuesta original."""
    base = getSampleStyleSheet()
    body = ParagraphStyle("gbody", parent=base["BodyText"], fontSize=10.5, leading=15)
    small = ParagraphStyle("gsmall", parent=body, fontSize=9, leading=12)
    habla = ParagraphStyle("habla", parent=body, fontSize=12.5, leading=19, leftIndent=8)
    h2 = ParagraphStyle("gh2", parent=base["Heading2"], spaceBefore=14, spaceAfter=4)
    h3 = ParagraphStyle("gh3", parent=base["Heading3"], spaceBefore=10, spaceAfter=2, textColor=colors.HexColor("#2B6CB0"))

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm,
                            title="PractIA — Guion final para practicar", author="PractIA")
    cmp = feedback.comparativo_referencia
    story: list = [
        _para("PractIA — Guion final para practicar", base["Title"]),
        _para(f"{case['company']} · {case['title']} ({case['industry']} · {case['case_type']})", body),
        _para(f"Generado el {date.today():%d/%m/%Y} · Tu evaluación: {feedback.puntaje_total}/100 · "
              f"Guion: ~{guion.palabras} palabras, ~{hhmmss(guion.segundos)} min", small),
        _para("Cómo usarlo", h2),
        _para("1) Léelo en voz alta dos veces. 2) Dilo mirando solo los títulos de cada bloque. 3) Grábate con el cronómetro de "
              "la app y evalúa de nuevo: apunta a pasar tu puntaje sin leer.", body),
        _para("1. Guion final", h2),
    ]
    t = 0
    for bloque in guion.bloques:
        story.append(KeepTogether([
            _para(f"{bloque.nombre} · {hhmmss(t)}–{hhmmss(t + bloque.segundos)}", h3),
            _para(bloque.texto, habla),
        ]))
        t += bloque.segundos
    if guion.cambios:
        story += [_para("2. Qué cambió respecto a tu respuesta", h2), *[_para(f"• {c}", body) for c in guion.cambios]]
    if cmp:
        story += [
            _para("3. Contraste con la respuesta de referencia", h2),
            _para("Coincidiste en: " + ("; ".join(cmp.coincide) or "—"), body),
            _para("Aportaste: " + ("; ".join(cmp.aporta) or "—"), body),
            _para("Te faltó: " + ("; ".join(cmp.le_falto) or "—"), body),
        ]
    if guion.consejos:
        story += [_para("4. Consejos para practicar", h2), *[_para(f"• {c}", body) for c in guion.consejos]]
    story += [_para("5. Tu respuesta original", h2), _para(transcript, small)]
    doc.build(story)
    return buffer.getvalue()
