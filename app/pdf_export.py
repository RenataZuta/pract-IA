"""
Exporta el feedback del evaluador a PDF con reportlab.

Solo arma el documento; la UI (app/main.py) lo ofrece con st.download_button.
"""
from __future__ import annotations

from datetime import date
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ai.evaluator import Feedback

# Helvetica solo cubre cp1252: se reemplazan los símbolos más comunes que
# escriben los LLM y lo demás se degrada a "?" en vez de romper el PDF.
_REEMPLAZOS = {
    "→": "->", "←": "<-", "−": "-", "≥": ">=", "≤": "<=", "≈": "~",
    " ": " ", "​": "",
}


def _safe(text: str) -> str:
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

    # Criterios: tabla con el comentario ajustado a la columna.
    filas = [[_para("Criterio", small), _para("Puntaje", small), _para("Comentario", small)]]
    for criterio in feedback.criterios:
        filas.append([
            _para(criterio.nombre, small),
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
