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
from ai.transcribe import ERROR_PREFIX, transcribe_audio  # noqa: E402
from app.pdf_export import feedback_to_pdf  # noqa: E402

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
    """Muestra el caso + anexos."""
    st.header(case["title"])
    st.caption(f"**{case['company']}** · {case['industry']} · {case['case_type']}")
    st.markdown("### Contexto")
    st.markdown(case["context"])

    if case.get("exhibits"):
        st.markdown("### Anexos")
        for i, exhibit in enumerate(case["exhibits"], 1):
            with st.expander(f"Anexo {i}: {exhibit['title']}"):
                st.markdown(exhibit["content"])

    st.markdown("### Lo que te piden")
    st.info(case["prompt"])


def timer_view() -> None:
    """Cronómetro de 3 fases."""
    st.sidebar.markdown("---")
    st.sidebar.subheader("⏱️ Cronómetro")
    st.sidebar.radio(
        "Fase actual",
        ["Lectura (15 min)", "Discusión (20 min)", "Conclusión (5 min)"],
    )

    if "phase_start" not in st.session_state:
        st.session_state.phase_start = None

    col1, col2 = st.sidebar.columns(2)
    if col1.button("Iniciar"):
        st.session_state.phase_start = time.time()
    if col2.button("Reiniciar"):
        st.session_state.phase_start = None

    if st.session_state.phase_start:
        elapsed = int(time.time() - st.session_state.phase_start)
        mins, secs = divmod(elapsed, 60)
        st.sidebar.metric("Transcurrido", f"{mins:02d}:{secs:02d}")


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
        st.session_state.update(audio_digest=digest, transcript_text=transcript, feedback=None)

    st.audio(audio_bytes)
    transcript = st.text_area(
        "Transcripción (puedes corregirla antes de evaluar)",
        key="transcript_text",
        height=200,
    )
    if transcript.startswith(ERROR_PREFIX):
        st.error(
            "No se pudo transcribir el audio. Revisa tu GROQ_API_KEY o vuelve a grabar; "
            "también puedes escribir tu respuesta a mano en el cuadro de arriba."
        )

    can_evaluate = bool(transcript.strip()) and not transcript.startswith(ERROR_PREFIX)
    if st.button("Evaluar respuesta", type="primary", disabled=not can_evaluate):
        with st.spinner("Evaluando tu respuesta..."):
            try:
                feedback = evaluate_response(transcript, case, load_rubric(industry))
            except EvaluationError as exc:
                st.error(f"No se pudo evaluar: {exc}")
            else:
                st.session_state.feedback = {
                    "case_id": case["id"],
                    "feedback": feedback,
                    "transcript": transcript,
                }

    saved = st.session_state.get("feedback")
    if saved and saved["case_id"] == case["id"]:
        feedback_view(saved["feedback"], case, saved["transcript"])


def feedback_view(feedback: Feedback, case: dict, transcript: str) -> None:
    """Muestra el feedback del evaluador y el botón para bajarlo en PDF."""
    st.markdown("---")
    st.markdown("### 📋 Tu feedback")
    st.metric("Puntaje total", f"{feedback.puntaje_total}/100")

    for criterio in feedback.criterios:
        st.progress(criterio.puntaje / 10, text=f"{criterio.nombre}: {criterio.puntaje}/10")
        with st.expander(f"Comentario — {criterio.nombre}"):
            st.write(criterio.comentario)

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


# ---------- Modo: Entrevista 1-a-1 ----------
def interview_page() -> None:
    """Pregunta aleatoria del banco según el tipo elegido (solo lectura por ahora)."""
    label = st.sidebar.selectbox("Tipo de pregunta", list(QUESTION_TYPES))
    tipo = QUESTION_TYPES[label]
    questions = load_questions().get(tipo, [])

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
    st.caption(f"{label} · {question['subtema']}")
    st.markdown(f"### {question['pregunta']}")
    st.caption("Respóndela en voz alta, como si el jefe final estuviera frente a ti.")
    with st.expander("Pista del entrevistador (míralo después de responder)"):
        st.write(question["hint"])
    st.info(
        "Por ahora este modo solo te muestra preguntas del banco. La grabación y el "
        "feedback STAR + técnica + fit llegan en la siguiente versión."
    )


# ---------- Main ----------
def main() -> None:
    mode = mode_selector()
    if mode == "Group case":
        industry, case = case_selector()
        case_view(case)
        timer_view()
        recording_view(case, industry)
    else:
        interview_page()


if __name__ == "__main__":
    main()
