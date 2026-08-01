"""
app.py
-----------------------------------------------------------------------------
API FastAPI del agente de soporte BimBam Buy — versión avanzada.

Endpoints:
    GET  /health              -> chequeo simple del servicio
    GET  /health/ready         -> el pipeline (índice + BM25) ya está listo
    POST /ask                  -> pregunta (texto) con memoria multi-turno
                                   por session_id
    POST /feedback              -> registra 👍/👎 sobre una respuesta anterior
    GET  /metrics                -> métricas Prometheus
    GET  /stats                   -> métricas agregadas (uso rápido en dashboards)
    POST /voice/ask                 -> pregunta por voz (audio in -> texto +
                                        audio out)

La cadena RAG (vector store + BM25 + reranker) se construye una sola vez al
iniciar el proceso (lifespan) para no reconstruir el índice en cada request.
-----------------------------------------------------------------------------
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import Response
from pydantic import BaseModel, Field

from rag.pipeline import get_pipeline
from rag.memory import new_session_id
from rag.graph import create_graph
from monitoring.logging_db import log_interaction, save_feedback, get_stats
from monitoring.metrics import (
    ERRORS_TOTAL,
    FEEDBACK_TOTAL,
    REQUESTS_TOTAL,
    metrics_response,
    record_result_metrics,
)
from voice.stt import transcribe_audio
from voice.tts import synthesize_speech

pipeline = None
graph = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pipeline, graph
    pipeline = get_pipeline()
    graph = create_graph()
    yield


app = FastAPI(
    title="BimBam Buy AI Support Agent",
    description=(
        "Agente RAG avanzado (hybrid search + reranking + memoria "
        "multi-turno + interfaz de voz) desarrollado para el Challenge "
        "Agente IA de Alura + Oracle Next Education (ONE)."
    ),
    version="2.0.0",
    lifespan=lifespan,
)


# --------------------------------------------------------------------------- #
# Esquemas
# --------------------------------------------------------------------------- #
class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, examples=["¿Cuánto tarda un reembolso?"])
    session_id: str | None = Field(
        default=None,
        description="Id de conversación para habilitar memoria multi-turno. "
        "Si se omite, se trata como una conversación nueva.",
    )


class AskResponse(BaseModel):
    interaction_id: int
    session_id: str
    question: str
    standalone_question: str
    answer: str
    sources: list[str]
    timings_ms: dict


class FeedbackRequest(BaseModel):
    interaction_id: int
    feedback: int = Field(..., description="1 = 👍 útil, -1 = 👎 no útil")


# --------------------------------------------------------------------------- #
# Salud
# --------------------------------------------------------------------------- #
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/ready")
def health_ready():
    if pipeline is None:
        raise HTTPException(status_code=503, detail="El agente todavía no está listo")
    return {"status": "ready"}


# --------------------------------------------------------------------------- #
# Ask (texto, multi-turno)
# --------------------------------------------------------------------------- #
@app.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest):
    if graph is None:
        raise HTTPException(status_code=503, detail="El agente todavía no está listo")

    REQUESTS_TOTAL.labels(endpoint="/ask").inc()
    session_id = payload.session_id or new_session_id()

    try:
        # Invocación del grafo
        result = graph.invoke({
            "question": payload.question,
            "session_id": session_id
        })
    except Exception as exc:  # noqa: BLE001
        ERRORS_TOTAL.labels(endpoint="/ask").inc()
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    record_result_metrics("/ask", result.get("timings_ms", {}))
    interaction_id = log_interaction(result)

    return {
        "interaction_id": interaction_id,
        "session_id": session_id,
        **result
    }


# --------------------------------------------------------------------------- #
# Feedback / observabilidad
# --------------------------------------------------------------------------- #
@app.post("/feedback")
def feedback(payload: FeedbackRequest):
    if payload.feedback not in (1, -1):
        raise HTTPException(status_code=400, detail="feedback debe ser 1 o -1")
    save_feedback(payload.interaction_id, payload.feedback)
    FEEDBACK_TOTAL.labels(type="up" if payload.feedback == 1 else "down").inc()
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    body, content_type = metrics_response()
    return Response(content=body, media_type=content_type)


@app.get("/stats")
def stats():
    return get_stats()


# --------------------------------------------------------------------------- #
# Administración / orquestación (usado por el flow de Kestra ingest_knowledge_base)
# --------------------------------------------------------------------------- #
class ReindexResponse(BaseModel):
    status: str
    chunks_indexed: int


@app.post("/admin/reindex", response_model=ReindexResponse)
def admin_reindex():
    """Reconstruye el índice (vector store + BM25) desde los PDFs en `data/`.

    Pensado para ser disparado por un orquestador externo (Kestra) cuando se
    agregan o actualizan documentos en la base de conocimiento, en vez de
    reconstruir el índice manualmente o reiniciar el proceso.
    """
    global pipeline
    if pipeline is None:
        raise HTTPException(status_code=503, detail="El agente todavía no está listo")

    try:
        pipeline.build(force_rebuild=True)
    except Exception as exc:  # noqa: BLE001
        ERRORS_TOTAL.labels(endpoint="/admin/reindex").inc()
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"status": "reindexed", "chunks_indexed": len(pipeline._chunks)}


# --------------------------------------------------------------------------- #
# Interfaz de voz: audio -> texto -> RAG -> texto -> audio
# --------------------------------------------------------------------------- #
@app.post("/voice/ask")
async def voice_ask(audio: UploadFile = File(...), session_id: str | None = None):
    """Recibe un audio (webm/mp3/wav), lo transcribe, lo procesa con el
    pipeline RAG y devuelve tanto el texto como el audio de la respuesta
    (en base64, ya que los headers HTTP no son seguros para texto en
    español con tildes/ñ).
    """
    if graph is None:
        raise HTTPException(status_code=503, detail="El agente todavía no está listo")

    import base64

    REQUESTS_TOTAL.labels(endpoint="/voice/ask").inc()
    t0 = time.perf_counter()

    audio_bytes = await audio.read()
    try:
        question_text = transcribe_audio(audio_bytes, filename=audio.filename or "audio.wav")
    except Exception as exc:  # noqa: BLE001
        ERRORS_TOTAL.labels(endpoint="/voice/ask").inc()
        raise HTTPException(status_code=500, detail=f"Error al transcribir el audio: {exc}") from exc

    session_id = session_id or new_session_id()
    
    # Invocación del grafo
    result = graph.invoke({
        "question": question_text,
        "session_id": session_id
    })
    
    record_result_metrics("/voice/ask", result.get("timings_ms", {}))
    interaction_id = log_interaction(result)

    try:
        audio_response = synthesize_speech(result["answer"])
    except Exception as exc:  # noqa: BLE001
        ERRORS_TOTAL.labels(endpoint="/voice/ask").inc()
        raise HTTPException(status_code=500, detail=f"Error al generar el audio: {exc}") from exc

    total_ms = round((time.perf_counter() - t0) * 1000, 1)

    return {
        "interaction_id": interaction_id,
        "session_id": session_id,
        "question_transcribed": question_text,
        "answer_text": result["answer"],
        "sources": result["sources"],
        "answer_audio_base64": base64.b64encode(audio_response).decode("ascii"),
        "audio_mime_type": "audio/mpeg",
        "total_latency_ms": total_ms,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
