"""
PractIA — Prep de group case y entrevista, por voz.

App Streamlit principal. Mantiene la lógica de orquestación aquí pero
delega transcripción, evaluación y PDF a los módulos en `ai/` y `app/`.
"""
from __future__ import annotations

import hashlib
import json
import random
import sys
import time
import unicodedata
from pathlib import Path

import pandas as pd
import streamlit as st
from audio_recorder_streamlit import audio_recorder
from dotenv import load_dotenv
from loguru import logger

# `streamlit run app/main.py` solo agrega app/ al sys.path; hace falta la raíz
# del repo para poder importar los paquetes `ai` y `app`.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai.evaluator import EvaluationError, Feedback, evaluate_response  # noqa: E402
from ai.guion import GuionError, generar_guion  # noqa: E402
from ai.rag import recuperar  # noqa: E402
from ai.transcribe import ERROR_PREFIX, transcribe_audio  # noqa: E402
from app.pdf_export import TIPO_TITULOS, feedback_to_pdf, guion_to_pdf  # noqa: E402
from app import verificacion_view  # noqa: E402
from app.theme import (  # noqa: E402
    ENTREVISTA, INDUSTRIAS, banda_generica, banda_html, css, icono_y_lema, mision_html, pasos_html, tema_de,
)

load_dotenv()

# ---------- Configuración ----------
st.set_page_config(
    page_title="PractIA — Prep de group case y entrevista",
    page_icon="🎙️",
    layout="wide",
)

CASES_DIR = ROOT / "ai" / "cases"
RUBRICS_DIR = ROOT / "ai" / "rubrics"
QUESTIONS_DIR = ROOT / "ai" / "questions"

MODES = ["Group case", "Entrevista 1-a-1"]

# Tipo de pregunta -> tema (las técnicas toman el color de su industria; STAR y fit, el del modo)
TEMA_TIPO = {
    "tecnica_banca": INDUSTRIAS["Banca"][0],
    "tecnica_fmcg": INDUSTRIAS["FMCG"][0],
    "tecnica_consultoria": INDUSTRIAS["Consultoría"][0],
}

# Etiqueta en el selector -> archivo en ai/questions/
QUESTION_TYPES = {
    "Behavioral STAR": "behavioral_star",
    "Técnica banca": "tecnica_banca",
    "Técnica FMCG": "tecnica_fmcg",
    "Técnica consultoría": "tecnica_consultoria",
    "Fit": "fit",
}


# ---------- Utilidades ----------
@st.cache_data
def load_cases() -> list[dict]:
    """Carga todos los casos semilla desde ai/cases/*.json."""
    cases = []
    for path in sorted(CASES_DIR.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            cases.append(json.load(f))
    return cases


@st.cache_data
def load_rubric(industry: str) -> dict:
    """Carga la rúbrica de la industria dada ("Consultoría" -> consultoria.json)."""
    slug = unicodedata.normalize("NFKD", industry).encode("ascii", "ignore").decode().lower()
    with open(RUBRICS_DIR / f"{slug}.json", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def load_questions() -> dict[str, list[dict]]:
    """Carga el banco de preguntas: {tipo: [{pregunta, hint, tipo, subtema}]}."""
    questions = {}
    for path in sorted(QUESTIONS_DIR.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            questions[path.stem] = json.load(f)
    return questions


# ---------- Sidebar ----------
def mode_selector() -> str:
    """Título y selector de modo; es lo primero que se pinta en el sidebar."""
    st.sidebar.title("🎙️ PractIA")
    st.sidebar.caption("Prep de group case y entrevista para prácticas")
    return st.sidebar.radio("Modo", MODES)


def case_selector() -> tuple[str, dict]:
    """Sidebar del group case: selección de industria, empresa y caso."""
    industry = st.sidebar.selectbox(
        "Industria",
        ["Banca", "FMCG", "Consultoría"],
    )

    cases = [c for c in load_cases() if c["industry"] == industry]
    case_titles = [f"{c['company']} — {c['title']}" for c in cases]
    choice = st.sidebar.selectbox("Caso", case_titles)
    case = cases[case_titles.index(choice)]

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        "**Duración total:** ~40 min\n\n"
        "- 15 min lectura\n"
        "- 20 min discusión (grabada)\n"
        "- 5 min conclusión"
    )
    return industry, case


# ---------- Modo: Group case ----------
def case_view(case: dict) -> None:
    """Muestra el caso con la identidad de su empresa: franja, contexto, anexos y misión."""
    tema = tema_de(case)
    icono, lema = icono_y_lema(case["industry"])
    st.markdown(css(tema), unsafe_allow_html=True)
    st.markdown(banda_html(case, tema, icono), unsafe_allow_html=True)
    st.header(case["title"])
    st.markdown("### Contexto")
    st.markdown(case["context"])

    if case.get("exhibits"):
        st.markdown("### Anexos")
        for i, exhibit in enumerate(case["exhibits"], 1):
            with st.expander(f"Anexo {i}: {exhibit['title']}"):
                st.markdown(exhibit["content"])

    verificacion_view.render(case["id"])

    st.markdown(mision_html(case, lema), unsafe_allow_html=True)


FASES = {  # fase -> minutos objetivo
    "Mi respuesta (3 min)": 3,
    "Lectura (15 min)": 15,
    "Discusión (20 min)": 20,
    "Conclusión (5 min)": 5,
}


def _reiniciar_reloj() -> None:
    st.session_state.phase_start = None


def timer_view() -> None:
    """Cronómetro con cuenta regresiva que corre solo; la fase fija el tiempo objetivo."""
    st.sidebar.markdown("---")
    st.sidebar.subheader("⏱️ Cronómetro")
    fase = st.sidebar.radio("Fase actual", list(FASES), key="fase", on_change=_reiniciar_reloj)
    st.session_state.setdefault("phase_start", None)

    col1, col2 = st.sidebar.columns(2)
    if col1.button("Iniciar"):
        st.session_state.phase_start = time.time()
    if col2.button("Reiniciar"):
        st.session_state.phase_start = None

    objetivo = FASES[fase] * 60
    corriendo = st.session_state.phase_start is not None

    # Un fragmento que se re-ejecuta cada segundo solo mientras corre: no recarga la
    # página ni interrumpe la grabación.
    @st.fragment(run_every=1 if corriendo else None)
    def reloj() -> None:
        inicio = st.session_state.phase_start
        if inicio is None:
            st.metric("Tiempo restante", f"{objetivo // 60:02d}:{objetivo % 60:02d}")
            st.caption("Pulsa Iniciar y empieza a hablar.")
            return
        transcurrido = int(time.time() - inicio)
        restante = objetivo - transcurrido
        if restante >= 0:
            st.metric("Tiempo restante", f"{restante // 60:02d}:{restante % 60:02d}")
            st.progress(min(transcurrido / objetivo, 1.0))
        else:
            exceso = -restante
            st.metric("Tiempo excedido", f"+{exceso // 60:02d}:{exceso % 60:02d}")
            st.error("¡Se acabó el tiempo! Cierra tu recomendación.")

    with st.sidebar:
        reloj()


def recording_view(case: dict, industry: str) -> None:
    """Grabación, transcripción editable y evaluación."""
    st.markdown("---")
    st.markdown("### 🎤 Graba tu respuesta")
    st.caption(
        "Al terminar la fase de discusión, graba tu recomendación final. "
        "Whisper transcribirá y el evaluador IA te dará feedback contra la rúbrica."
    )

    recorded = audio_recorder(
        text="Haz clic para grabar (se detiene tras 3 s de silencio)",
        pause_threshold=3.0,
        sample_rate=16000,
        key="recorder",
    )
    # Respaldo si el navegador no da acceso al micrófono.
    with st.expander("¿No funciona el micrófono? Sube un audio"):
        uploaded = st.file_uploader(
            "Audio (MP3, WAV, M4A, WEBM)",
            type=["mp3", "wav", "m4a", "webm"],
            key="uploader",
        )
    audio_bytes = (uploaded.getvalue() if uploaded else None) or recorded
    if not audio_bytes:
        return

    # Streamlit re-ejecuta el script en cada interacción y el grabador devuelve
    # el mismo audio: solo se transcribe cuando el audio cambia.
    digest = hashlib.sha256(audio_bytes).hexdigest()
    if st.session_state.get("audio_digest") != digest:
        with st.spinner("Transcribiendo con Whisper..."):
            transcript = transcribe_audio(audio_bytes)
        logger.info("Audio transcrito ({} bytes, {} chars)", len(audio_bytes), len(transcript))
        st.session_state.update(audio_digest=digest, audio_transcript=transcript, feedback=None, guion=None)

    st.audio(audio_bytes)
    # Una clave por audio: el texto editado se conserva en cada rerun y un audio
    # nuevo arranca con su transcripción. Fijar el valor vía session_state con una
    # clave fija no se pinta en el navegador cuando la corrida la dispara una subida.
    transcript = st.text_area(
        "Transcripción (puedes corregirla antes de evaluar)",
        value=st.session_state.audio_transcript,
        key=f"transcript_{digest}",
        height=200,
    )
    if transcript.startswith(ERROR_PREFIX):
        st.error(
            "No se pudo transcribir el audio. Revisa tu GROQ_API_KEY o vuelve a grabar; "
            "también puedes escribir tu respuesta a mano en el cuadro de arriba."
        )

    can_evaluate = bool(transcript.strip()) and not transcript.startswith(ERROR_PREFIX)
    previo = st.session_state.get("feedback")
    ya_evaluada = bool(previo and previo["case_id"] == case["id"] and previo["transcript"] == transcript)
    if st.button("Evaluar respuesta", type="primary", disabled=not can_evaluate):
        if ya_evaluada:  # misma respuesta, mismo caso: otra llamada gastaría ~6K tokens para el mismo resultado
            st.info("Esta respuesta ya está evaluada. Edita el texto si quieres evaluar una versión nueva.")
        else:
            with st.spinner("Evaluando tu respuesta..."):
                try:
                    feedback = evaluate_response(transcript, case, load_rubric(industry))
                except EvaluationError as exc:
                    st.error(f"No se pudo evaluar: {exc}")
                else:
                    st.session_state.guion = None
                    st.session_state.setdefault("historial", {}).setdefault(case["id"], []).append(
                        {"total": feedback.puntaje_total, "por_tipo": dict(feedback.puntaje_por_tipo)}
                    )
                    st.session_state.feedback = {
                        "case_id": case["id"],
                        "feedback": feedback,
                        "transcript": transcript,
                    }

    saved = st.session_state.get("feedback")
    if saved and saved["case_id"] == case["id"]:
        feedback_view(saved["feedback"], case, saved["transcript"])


def coherencia_view(feedback: Feedback, case: dict) -> None:
    """Avisa de cifras del feedback que no salen del caso (revisión por código, sin tokens; nunca rompe la vista)."""
    try:
        from ai.verifier.coherencia import revisar_feedback

        alertas = revisar_feedback(feedback, case)
    except Exception as exc:
        logger.warning("No se pudo revisar la coherencia del feedback: {}", exc)
        return
    if not alertas:
        st.caption("✅ Las cifras del feedback salen del contexto y los anexos del caso.")
        return
    with st.expander(f"⚠️ {len(alertas)} cifra(s) del feedback no aparecen en el caso"):
        st.caption("Pueden ser cálculos del evaluador (un ratio, una diferencia) o errores: compáralas con los anexos.")
        for a in alertas:
            st.markdown(f"- **{a.cifra}** en {a.donde}: «…{a.frase}…»")


def feedback_view(feedback: Feedback, case: dict, transcript: str) -> None:
    """Muestra el feedback del evaluador y el botón para bajarlo en PDF."""
    st.markdown("---")
    st.markdown("### 📋 Tu feedback")
    historial = st.session_state.get("historial", {}).get(case["id"], [])
    delta = f"{historial[-1]['total'] - historial[-2]['total']:+d} vs intento anterior" if len(historial) >= 2 else None
    st.metric("Puntaje total", f"{feedback.puntaje_total}/100", delta=delta)
    if len(historial) >= 2:
        with st.expander(f"Tu progreso en este caso ({len(historial)} intentos)"):
            st.line_chart(pd.DataFrame({"Intento": range(1, len(historial) + 1),
                                        "Puntaje total": [h["total"] for h in historial]}).set_index("Intento"))

    if feedback.puntaje_por_tipo:
        columnas = st.columns(len(feedback.puntaje_por_tipo))
        for columna, (tipo, puntaje) in zip(columnas, feedback.puntaje_por_tipo.items()):
            columna.metric(TIPO_TITULOS.get(tipo, tipo), f"{puntaje}/100")

    for tipo in dict.fromkeys(c.tipo for c in feedback.criterios):
        st.markdown(f"**{TIPO_TITULOS.get(tipo, 'Criterios')}**")
        for criterio in (c for c in feedback.criterios if c.tipo == tipo):
            peso = f" ({criterio.peso * 100:.0f} %)" if criterio.peso else ""
            st.progress(criterio.puntaje / 10, text=f"{criterio.nombre}{peso}: {criterio.puntaje}/10")
            with st.expander(f"Comentario — {criterio.nombre}"):
                st.write(criterio.comentario)
        if tipo == "blando":
            st.caption(
                "Las habilidades blandas se estiman por lo que dices y cómo lo dices; "
                "no reemplazan una dinámica grupal real."
            )

    comparativo = feedback.comparativo_referencia
    if comparativo:
        st.markdown("**Comparativo con la respuesta de referencia**")
        titulos = ("Coincidiste en", "Aportaste", "Te faltó")
        listas = (comparativo.coincide, comparativo.aporta, comparativo.le_falto)
        for columna, titulo, items in zip(st.columns(3), titulos, listas):
            columna.markdown(f"*{titulo}*")
            columna.markdown("\n".join(f"- {item}" for item in items) or "- —")
    referencia = case.get("respuesta_referencia") or case.get("pista_respuesta_modelo")
    if referencia:
        with st.expander("Ver la respuesta de referencia (preparada con Claude)"):
            st.info(referencia)
    if feedback.fuentes_recuperadas:
        with st.expander(f"Material recuperado por RAG ({len(feedback.fuentes_recuperadas)} fragmentos)"):
            st.caption("Fragmentos del corpus de PractIA que el evaluador usó para contrastar tu respuesta.")
            for fuente in feedback.fuentes_recuperadas:
                st.markdown(f"- {fuente}")
    punto_debil_view(feedback, case)

    st.success(f"**Fortaleza principal:** {feedback.fortaleza_principal}")
    st.warning(
        "**Tres cosas a mejorar:**\n"
        + "\n".join(f"- {item}" for item in feedback.tres_cosas_a_mejorar)
    )
    if feedback.red_flags_detectados:
        st.error(
            "**Red flags detectados:**\n"
            + "\n".join(f"- {item}" for item in feedback.red_flags_detectados)
        )
    with st.expander("Ver respuesta modelo"):
        st.info(feedback.respuesta_modelo)

    st.download_button(
        "Descargar feedback como PDF",
        data=feedback_to_pdf(feedback, case, transcript),
        file_name="feedback_practia.pdf",
        mime="application/pdf",
    )

    coherencia_view(feedback, case)
    guion_view(feedback, case, transcript)


def punto_debil_view(feedback: Feedback, case: dict) -> None:
    """Preguntas reales del banco (vía RAG, sin gastar tokens) para entrenar el criterio más bajo."""
    if not feedback.criterios:
        return
    debil = min(feedback.criterios, key=lambda c: c.puntaje)
    if debil.puntaje > 7:
        return
    descripcion = next((c["descripcion"] for c in load_rubric(case["industry"])["criterios"] if c["nombre"] == debil.nombre), "")
    preguntas = recuperar(f"{debil.nombre}. {descripcion}", k=2, solo_preguntas=True)
    if not preguntas:
        return
    with st.expander(f"🏋️ Entrena tu punto más débil: {debil.nombre} ({debil.puntaje}/10)"):
        st.caption("Preguntas reales del banco relacionadas con ese criterio. Respóndelas en voz alta en el modo Entrevista 1-a-1.")
        for doc, _ in preguntas:
            st.markdown(f"**{doc.titulo}**")
            st.write(doc.texto)


def guion_view(feedback: Feedback, case: dict, transcript: str) -> None:
    """Genera (a pedido) un guion final que combina tu respuesta con el contraste de la IA, en un solo PDF."""
    st.markdown("---")
    st.markdown("### 🎯 Practica con un guion final")
    st.caption(
        "Combina tu respuesta con el contraste de la IA en un guion de ~3 minutos, con tiempos por bloque, "
        "y lo baja en un solo PDF junto con tu respuesta original. Si acabas de evaluar, espera ~1 minuto "
        "(límite del plan gratuito de Groq)."
    )
    clave = hashlib.sha1(f"{case['id']}|{transcript}".encode()).hexdigest()
    if st.button("Generar guion final"):
        with st.spinner("Armando tu guion final..."):
            try:
                guion = generar_guion(transcript, case, feedback)
            except GuionError as exc:
                st.error(f"No se pudo generar el guion: {exc}. Si Groq está limitando, espera un minuto y vuelve a intentar.")
            else:
                st.session_state.guion = {"clave": clave, "guion": guion}

    guardado = st.session_state.get("guion")
    if guardado and guardado["clave"] == clave:
        guion = guardado["guion"]
        st.success(f"Guion listo: ~{guion.palabras} palabras, ~{guion.segundos // 60}:{guion.segundos % 60:02d} min.")
        with st.expander("Ver el guion final"):
            for bloque in guion.bloques:
                st.markdown(f"**{bloque.nombre}** ({bloque.segundos} s)")
                st.write(bloque.texto)
            if guion.cambios:
                st.markdown("**Qué cambió respecto a tu respuesta**")
                st.markdown("\n".join(f"- {c}" for c in guion.cambios))
        st.download_button(
            "Descargar guion final (PDF)",
            data=guion_to_pdf(guion, case, feedback, transcript),
            file_name="guion_final_practia.pdf",
            mime="application/pdf",
        )


# ---------- Modo: Entrevista 1-a-1 ----------
def interview_page() -> None:
    """Pregunta aleatoria del banco según el tipo elegido (solo lectura por ahora)."""
    label = st.sidebar.selectbox("Tipo de pregunta", list(QUESTION_TYPES))
    tipo = QUESTION_TYPES[label]
    questions = load_questions().get(tipo, [])

    tema = TEMA_TIPO.get(tipo, ENTREVISTA)
    st.markdown(css(tema), unsafe_allow_html=True)
    st.header("Entrevista 1-a-1 con el jefe final")
    if not questions:
        st.warning(f"No hay preguntas cargadas para «{label}» en ai/questions/.")
        return

    new_question = st.sidebar.button("🎲 Otra pregunta")
    current = st.session_state.get("interview_question")
    if new_question or current is None or current["tipo"] != tipo:
        previous = current["question"] if current else None
        # load_questions() (cache_data) devuelve copias: se compara por valor, no por identidad.
        options = [q for q in questions if q != previous] or questions
        current = {"tipo": tipo, "question": random.choice(options)}
        st.session_state.interview_question = current

    question = current["question"]
    st.markdown(banda_generica("🎙️ Práctica con el jefe final", [label, question["subtema"]], tema), unsafe_allow_html=True)
    st.markdown(f"### {question['pregunta']}")
    st.caption("Respóndela en voz alta, como si el jefe final estuviera frente a ti.")
    with st.expander("Pista del entrevistador (míralo después de responder)"):
        st.write(question["hint"])
    st.info(
        "Por ahora este modo solo te muestra preguntas del banco. La grabación y el "
        "feedback STAR + técnica + fit llegan en la siguiente versión."
    )


# ---------- Main ----------
def _paso_actual(case: dict) -> int:
    """Paso del recorrido: 2 responder, 3 evaluar, 4 guion final, 5 todo hecho."""
    guardado = st.session_state.get("feedback")
    if guardado and guardado["case_id"] == case["id"]:
        return 5 if st.session_state.get("guion") else 4
    return 3 if st.session_state.get("audio_digest") else 2


def main() -> None:
    mode = mode_selector()
    if mode == "Group case":
        industry, case = case_selector()
        pasos = st.container()  # se llena al final, cuando el estado de esta corrida ya está actualizado
        case_view(case)
        timer_view()
        recording_view(case, industry)
        pasos.markdown(pasos_html(_paso_actual(case)), unsafe_allow_html=True)
    else:
        interview_page()


if __name__ == "__main__":
    main()
