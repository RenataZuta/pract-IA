"""
Transcribe en batch los audios de las 3 entrevistas de validación.

Uso:
    python scripts/transcribe_batch.py

Espera encontrar los audios en:
    data/audios/entrevista_01_banca.m4a   (o .mp3, .wav, .webm)
    data/audios/entrevista_02_fmcg.m4a
    data/audios/entrevista_03_consultoria.m4a

Guarda las transcripciones crudas en:
    data/transcripts/entrevista_0X_cruda.txt

Las notas limpias (en docs/research/entrevista-0X.md) se escriben a mano
después usando la plantilla del PDF de guías.
"""
from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

# Importar relativo al proyecto
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ai.transcribe import transcribe_file  # noqa: E402

load_dotenv()

AUDIO_DIR = ROOT / "data" / "audios"
OUTPUT_DIR = ROOT / "data" / "transcripts"

AUDIO_PATTERNS = [
    ("entrevista_01_banca", "banca"),
    ("entrevista_02_fmcg", "fmcg"),
    ("entrevista_03_consultoria", "consultoria"),
]

AUDIO_EXTS = [".m4a", ".mp3", ".wav", ".webm", ".ogg"]


def find_audio(stem: str) -> Path | None:
    for ext in AUDIO_EXTS:
        candidate = AUDIO_DIR / f"{stem}{ext}"
        if candidate.exists():
            return candidate
    return None


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for stem, industry in AUDIO_PATTERNS:
        audio_path = find_audio(stem)
        if not audio_path:
            logger.warning(f"No se encontró audio para {stem} en {AUDIO_DIR}")
            continue

        logger.info(f"Transcribiendo {audio_path.name} ({industry})...")
        text = transcribe_file(audio_path, language="es")

        output_path = OUTPUT_DIR / f"{stem}_cruda.txt"
        output_path.write_text(text, encoding="utf-8")
        logger.success(f"Guardado en {output_path} ({len(text)} chars)")


if __name__ == "__main__":
    main()
