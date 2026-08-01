"""
rag_engine.py
-----------------------------------------------------------------------------
Punto de entrada de compatibilidad hacia el pipeline avanzado (`rag/pipeline.py`).

Se mantiene este módulo en la raíz para no romper `cli.py`, `streamlit_app.py`
ni integraciones que ya importaban `rag_engine.answer_question`. Internamente
delega TODO al pipeline avanzado: recuperación híbrida (BM25 + vectorial con
RRF), reranking con cross-encoder, memoria conversacional multi-turno y
soporte OCR en la carga de documentos.

Ver README -> "Arquitectura avanzada" para el detalle de cada etapa.
-----------------------------------------------------------------------------
"""

from typing import Optional

from rag.pipeline import RagPipeline, get_pipeline  # noqa: F401
from rag.memory import new_session_id  # noqa: F401


def answer_question(
    question: str, session_id: str = "default", pipeline: Optional[RagPipeline] = None
) -> dict:
    """Responde una pregunta usando el pipeline RAG avanzado (hybrid search +
    reranking + memoria multi-turno). `session_id` identifica la conversación
    para habilitar preguntas de seguimiento ("¿y si pagué con transferencia?").
    """
    pipeline = pipeline or get_pipeline()
    return pipeline.ask(question, session_id=session_id)


if __name__ == "__main__":
    # Ejecutar `python rag_engine.py` construye/actualiza el índice (vector + BM25).
    print("Construyendo el índice (vectorial + BM25) a partir de los PDFs en 'data/'...")
    get_pipeline(force_rebuild=True)
    print("Listo.")
