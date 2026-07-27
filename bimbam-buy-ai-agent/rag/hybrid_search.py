"""
rag/hybrid_search.py
-----------------------------------------------------------------------------
Búsqueda híbrida (keyword + semántica), siguiendo el patrón enseñado en
llm-zoomcamp (06-best-practices/lessons/02-hybrid-search.md):

    - Búsqueda por keywords con BM25 (buena para códigos de orden, nombres
      exactos, términos técnicos: "OCI", "retracto", "48 horas").
    - Búsqueda semántica con embeddings + ChromaDB (buena para paráfrasis y
      preguntas conceptuales: "¿qué pasa si me arrepentí de la compra?").
    - Fusión de ambos rankings con Reciprocal Rank Fusion (RRF), que combina
      las *posiciones* de cada lista en vez de mezclar scores en escalas
      distintas (similaridad coseno vs. score BM25), evitando el problema de
      normalización.

RRF(d) = Σ 1 / (k + rank_i(d))   para cada lista de resultados i en la que
aparece el documento d. k amortigua el peso de las posiciones más bajas
(valor típico: 60).
-----------------------------------------------------------------------------
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

from rag.config import BM25_TOP_K, RRF_K, VECTOR_TOP_K


def _tokenize(text: str) -> List[str]:
    """Tokenización simple (lowercase + split) suficiente para BM25 en español."""
    return text.lower().split()


@dataclass
class BM25Index:
    """Índice BM25 construido sobre los mismos chunks que el vector store."""

    documents: List[Document] = field(default_factory=list)
    _bm25: BM25Okapi | None = field(default=None, init=False, repr=False)

    @classmethod
    def from_documents(cls, documents: List[Document]) -> "BM25Index":
        index = cls(documents=documents)
        corpus = [_tokenize(doc.page_content) for doc in documents]
        index._bm25 = BM25Okapi(corpus)
        return index

    def search(self, query: str, top_k: int = BM25_TOP_K) -> List[Document]:
        if self._bm25 is None:
            raise RuntimeError("El índice BM25 no fue inicializado")
        scores = self._bm25.get_scores(_tokenize(query))
        ranked_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        return [self.documents[i] for i in ranked_idx[:top_k] if scores[i] > 0]


def _doc_key(doc: Document) -> str:
    """Clave estable para identificar un chunk (fuente + página + hash de texto)."""
    return f"{doc.metadata.get('source')}|{doc.metadata.get('page')}|{hash(doc.page_content)}"


def reciprocal_rank_fusion(
    ranked_lists: List[List[Document]], k: int = RRF_K
) -> List[Document]:
    """Fusiona varias listas ordenadas de documentos usando RRF.

    Devuelve una única lista de documentos ordenada por score RRF descendente,
    sin duplicados.
    """
    scores: Dict[str, float] = {}
    doc_by_key: Dict[str, Document] = {}

    for ranked_list in ranked_lists:
        for rank, doc in enumerate(ranked_list):
            key = _doc_key(doc)
            doc_by_key[key] = doc
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)

    ordered_keys = sorted(scores, key=lambda key: scores[key], reverse=True)
    return [doc_by_key[key] for key in ordered_keys]


class HybridRetriever:
    """Combina búsqueda vectorial (Chroma) y BM25, fusionadas con RRF.

    Actúa como "stage 1" de un pipeline de dos etapas: recupera un pool
    amplio de candidatos con buen recall; el reranker (stage 2, ver
    `rag/reranker.py`) se encarga de la precisión final.
    """

    def __init__(self, vectorstore, bm25_index: BM25Index):
        self.vectorstore = vectorstore
        self.bm25_index = bm25_index

    def get_candidates(
        self, query: str, vector_k: int = VECTOR_TOP_K, bm25_k: int = BM25_TOP_K
    ) -> List[Document]:
        vector_results = self.vectorstore.similarity_search(query, k=vector_k)
        bm25_results = self.bm25_index.search(query, top_k=bm25_k)
        return reciprocal_rank_fusion([vector_results, bm25_results])
