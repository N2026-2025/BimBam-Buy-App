"""
voice/tts.py
-----------------------------------------------------------------------------
Text-to-Speech (TTS) para la interfaz de voz del agente.

Convierte la respuesta del agente en audio (mp3) usando la API de OpenAI.
Igual que en `stt.py`, la función está aislada para poder reemplazar el
proveedor (ElevenLabs, Azure Speech, Coqui TTS local, etc.) sin tocar
`app.py`.
-----------------------------------------------------------------------------
"""

from __future__ import annotations

from rag.config import TTS_MODEL, TTS_VOICE


def synthesize_speech(text: str) -> bytes:
    """Convierte texto a audio (mp3) y devuelve los bytes del archivo."""
    from openai import OpenAI

    client = OpenAI()
    response = client.audio.speech.create(
        model=TTS_MODEL,
        voice=TTS_VOICE,
        input=text,
    )
    return response.read()
