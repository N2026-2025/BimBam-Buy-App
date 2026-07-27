"""
rag/reranker.py
-----------------------------------------------------------------------------
Reranking con cross-encoder, siguiendo el patrón de
llm-zoomcamp (06-best-practices/lessons/03-reranking.md):

Un cross-encoder recibe la pregunta y CADA candidato juntos (a diferencia
de los embeddings, que los codifican por separado) y produce un score de
relevancia mucho más preciso. Es más lento que la búsqueda vectorial/BM25,
por eso se aplica solo sobre el pool reducido que ya filtró la etapa de
recuperación híbrida (stage 1), no sobre toda la base de conocimiento.

Pipeline de dos etapas:
    Stage 1 (recall):    Hybrid Search (BM25 + vectorial) + RRF -> ~10-20 candidatos
    Stage 2 (precisión): Cross-Encoder reranking               -> top-N final para el LLM
-----------------------------------------------------------------------------
"""

from __future__ import annotations

from functools import lru_cache
from typing import List

from langchain_core.documents import Document

from rag.config import RERANK_TOP_N, RERANKER_MODEL


@lru_cache(maxsize=1)
def _get_cross_encoder():
    """Carga (una sola vez, cacheada) el modelo cross-encoder de reranking."""
    from sentence_transformers import CrossEncoder

    return CrossEncoder(RERANKER_MODEL)


def rerank(query: str, candidates: List[Document], top_n: int = RERANK_TOP_N) -> List[Document]:
    """Reordena `candidates` por relevancia real respecto a `query` y devuelve
    los `top_n` mejores, cada uno con el score de reranking en su metadata
    (`rerank_score`) para trazabilidad/observabilidad.
    """
    if not candidates:
        return []

    model = _get_cross_encoder()
    pairs = [(query, doc.page_content) for doc in candidates]
    scores = model.predict(pairs)

    scored = list(zip(candidates, scores))
    scored.sort(key=lambda pair: pair[1], reverse=True)

    reranked_docs = []
    for doc, score in scored[:top_n]:
        doc.metadata["rerank_score"] = float(score)
        reranked_docs.append(doc)

    return reranked_docs
