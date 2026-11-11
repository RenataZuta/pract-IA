"""
Transcripción de audio con Whisper vía Groq.

Lee GROQ_API_KEY y GROQ_WHISPER_MODEL del .env (ver .env.example).
Si algo falla devuelve un string con prefijo "[ERROR_WHISPER]" en vez de
lanzar excepción, para que la UI pueda mostrarlo sin romperse.
"""
from __future__ import annotations

import os
from pathlib import Path

from groq import Groq
from loguru import logger

ERROR_PREFIX = "[ERROR_WHISPER]"

# Firma (magic bytes) -> nombre de archivo. Groq decide el formato por la
# extensión, y audio_recorder entrega WAV mientras el uploader acepta varios.
_AUDIO_SIGNATURES: tuple[tuple[int, bytes, str], ...] = (
    (0, b"RIFF", "audio.wav"),
    (0, b"\x1a\x45\xdf\xa3", "audio.webm"),
    (0, b"ID3", "audio.mp3"),
    (0, b"\xff\xfb", "audio.mp3"),
    (4, b"ftyp", "audio.m4a"),
    (0, b"OggS", "audio.ogg"),
    (0, b"fLaC", "audio.flac"),
)


def _guess_filename(audio_bytes: bytes) -> str:
    """Nombre de archivo según el formato real del audio (webm por defecto)."""
    for offset, signature, filename in _AUDIO_SIGNATURES:
        if audio_bytes[offset : offset + len(signature)] == signature:
            return filename
    return "audio.webm"


def transcribe_audio(audio_bytes: bytes, language: str = "es") -> str:
    """
    Transcribe un audio en memoria y devuelve el texto.

    Args:
        audio_bytes: contenido crudo del audio (wav, mp3, m4a, webm, ogg, flac).
        language: código ISO, por defecto "es" (español).

    Returns:
        Transcripción como string, o "[ERROR_WHISPER] <detalle>" si falla.
    """
    if not audio_bytes:
        logger.warning("transcribe_audio recibió un audio vacío.")
        return f"{ERROR_PREFIX} El audio está vacío."

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.error("Falta GROQ_API_KEY en el entorno (.env).")
        return f"{ERROR_PREFIX} Falta GROQ_API_KEY en el .env."

    try:
        client = Groq(api_key=api_key)
        response = client.audio.transcriptions.create(
            model=os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3"),
            file=(_guess_filename(audio_bytes), audio_bytes),
            language=language,
        )
        return response.text.strip()
    except Exception as exc:  # red, rate limit, key inválida, formato no soportado
        # Sin traceback: loguru imprimiría las variables locales (audio y API key).
        logger.error("Falló la transcripción con Groq Whisper ({}): {}", type(exc).__name__, exc)
        return f"{ERROR_PREFIX} {exc}"


def transcribe_file(path: str | Path, language: str = "es") -> str:
    """Helper para transcribir un archivo del disco."""
    with open(path, "rb") as f:
        return transcribe_audio(f.read(), language=language)
