"""
voice/stt.py
-----------------------------------------------------------------------------
Speech-to-Text (STT) para la interfaz de voz del agente.

Usa la API de Whisper de OpenAI (`audio.transcriptions`). Si se necesita un
proveedor 100% self-hosted/offline (por ejemplo para no depender de una API
externa), se puede reemplazar `transcribe_audio()` por `faster-whisper`
corriendo localmente sin cambiar la firma de la función ni el resto del
pipeline de voz (`voice/tts.py`, endpoint `/voice/ask` en `app.py`).
-----------------------------------------------------------------------------
"""

from __future__ import annotations

import io

from rag.config import STT_MODEL


def transcribe_audio(audio_bytes: bytes, filename: str = "audio.wav") -> str:
    """Transcribe un audio (bytes) a texto en español."""
    from openai import OpenAI

    client = OpenAI()
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = filename  # la librería de OpenAI usa el nombre para inferir el formato

    transcript = client.audio.transcriptions.create(
        model=STT_MODEL,
        file=audio_file,
        language="es",
    )
    return transcript.text
