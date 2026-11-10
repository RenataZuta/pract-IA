"""
Transcripción de audio con Whisper.

Soporta dos proveedores: OpenAI Whisper API y Hugging Face Inference.
Elegir con la variable WHISPER_PROVIDER en .env.
"""
from __future__ import annotations

import os
from io import BytesIO
from pathlib import Path

from loguru import logger


def transcribe_audio(audio_bytes: bytes, language: str = "es") -> str:
    """
    Transcribe un audio en memoria y devuelve el texto.

    Args:
        audio_bytes: contenido crudo del audio (wav, mp3, m4a, webm).
        language: código ISO, por defecto "es" (español).

    Returns:
        Transcripción como string.
    """
    provider = os.getenv("WHISPER_PROVIDER", "openai")
    if provider == "openai":
        return _transcribe_openai(audio_bytes, language)
    elif provider == "huggingface":
        return _transcribe_hf(audio_bytes, language)
    else:
        raise ValueError(f"WHISPER_PROVIDER desconocido: {provider}")


def _transcribe_openai(audio_bytes: bytes, language: str) -> str:
    """Usa la API de OpenAI (modelo whisper-1)."""
    # TODO Claude Code:
    # from openai import OpenAI
    # client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    # audio_file = BytesIO(audio_bytes)
    # audio_file.name = "audio.webm"  # OpenAI necesita el .name
    # response = client.audio.transcriptions.create(
    #     model=os.getenv("WHISPER_MODEL", "whisper-1"),
    #     file=audio_file,
    #     language=language,
    # )
    # return response.text
    logger.warning("Whisper OpenAI es stub — conectar.")
    return "[STUB] Transcripción pendiente."


def _transcribe_hf(audio_bytes: bytes, language: str) -> str:
    """Usa Hugging Face Inference para whisper-large-v3-turbo."""
    # TODO Claude Code: implementar con requests.post a la Inference API
    logger.warning("Whisper HF es stub — conectar.")
    return "[STUB] Transcripción pendiente."


def transcribe_file(path: str | Path, language: str = "es") -> str:
    """Helper para transcribir un archivo del disco."""
    with open(path, "rb") as f:
        return transcribe_audio(f.read(), language=language)
