"""
PractIA — Simulador de group case por voz.

App Streamlit principal. Mantiene la lógica de orquestación aquí pero
delega transcripción y evaluación a los módulos en `ai/`.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from loguru import logger

# Imports internos — se crean en los siguientes pasos de Claude Code
# from ai.transcribe import transcribe_audio
# from ai.evaluator import evaluate_response

load_dotenv()

# ---------- Configuración ----------
st.set_page_config(
    page_title="PractIA — Simulador de group case",
    page_icon="🎙️",
    layout="wide",
)

CASES_DIR = Path(__file__).parent.parent / "ai" / "cases"
RUBRICS_DIR = Path(__file__).parent.parent / "ai" / "rubrics"


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
    """Carga la rúbrica de la industria dada."""
    path = RUBRICS_DIR / f"{industry.lower()}.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------- UI ----------
def sidebar() -> tuple[str, dict]:
    """Sidebar: selección de industria, empresa y caso."""
    st.sidebar.title("🎙️ PractIA")
    st.sidebar.caption("Simulador de group case para prácticas")

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
    phase = st.sidebar.radio(
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
    """Grabación y evaluación."""
    st.markdown("---")
    st.markdown("### 🎤 Graba tu respuesta")
    st.caption(
        "Al terminar la fase de discusión, graba tu recomendación final. "
        "Whisper transcribirá y el evaluador IA te dará feedback contra la rúbrica."
    )

    # TODO Claude Code:
    # 1. Reemplazar con audio_recorder_streamlit.audio_recorder()
    # 2. Pasar el audio a ai.transcribe.transcribe_audio(audio_bytes)
    # 3. Pasar la transcripción a ai.evaluator.evaluate_response(
    #       transcript, case, rubric=load_rubric(industry))
    # 4. Mostrar el feedback estructurado

    uploaded = st.file_uploader(
        "O sube un audio (MP3, WAV, M4A)",
        type=["mp3", "wav", "m4a", "webm"],
    )
    if uploaded is not None and st.button("Evaluar"):
        with st.spinner("Transcribiendo..."):
            # transcript = transcribe_audio(uploaded.read())
            transcript = "[STUB] Transcripción pendiente — conectar Whisper."
            st.text_area("Transcripción", transcript, height=200)

        with st.spinner("Evaluando..."):
            # rubric = load_rubric(industry)
            # feedback = evaluate_response(transcript, case, rubric)
            feedback = {
                "scores": {
                    "framework": 0,
                    "numeros": 0,
                    "recomendacion": 0,
                    "tiempo": 0,
                },
                "fortaleza": "[STUB] Conectar evaluador.",
                "mejorar": ["[STUB]"],
                "respuesta_modelo": "[STUB]",
            }
            st.json(feedback)


# ---------- Main ----------
def main() -> None:
    industry, case = sidebar()
    case_view(case)
    timer_view()
    recording_view(case, industry)


if __name__ == "__main__":
    main()
