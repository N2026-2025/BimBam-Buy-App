"""
evaluation/evaluate_retrieval.py
-----------------------------------------------------------------------------
Evalúa la calidad del retrieval con las métricas estándar de
llm-zoomcamp 02-vector-search / 04-evaluation:

    - Hit Rate @ k: ¿el chunk correcto aparece entre los top-k resultados?
    - MRR @ k (Mean Reciprocal Rank): promedia 1 / posición del chunk
      correcto (0 si no aparece). Premia que el resultado correcto esté lo
      más arriba posible, no solo "presente".

Compara 3 estrategias sobre el mismo dataset (`ground_truth.csv`):
    1. Solo búsqueda vectorial (embeddings)
    2. Solo BM25 (keywords)
    3. Híbrida (BM25 + vectorial con RRF) + reranking con cross-encoder

Uso:
    python -m evaluation.generate_ground_truth   # (una vez)
    python -m evaluation.evaluate_retrieval
-----------------------------------------------------------------------------
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Callable, List

from langchain_core.documents import Document

from rag.config import PERSIST_DIR, COLLECTION_NAME, RERANK_TOP_N
from rag.hybrid_search import BM25Index, HybridRetriever
from rag.pipeline import get_embeddings, load_and_split
from rag.reranker import rerank
from langchain_community.vectorstores import Chroma

GROUND_TRUTH_PATH = Path(__file__).resolve().parent / "ground_truth.csv"
RESULTS_PATH = Path(__file__).resolve().parent / "results" / "retrieval_metrics.md"
TOP_K = 5


def _load_ground_truth() -> List[dict]:
    if not GROUND_TRUTH_PATH.exists():
        raise FileNotFoundError(
            f"No existe {GROUND_TRUTH_PATH}. Corré primero: "
            "python -m evaluation.generate_ground_truth"
        )
    with open(GROUND_TRUTH_PATH, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def hit_rate(results: List[List[int]], relevant_ids: List[int]) -> float:
    hits = sum(1 for res, rel in zip(results, relevant_ids) if rel in res)
    return hits / len(results) if results else 0.0


def mrr(results: List[List[int]], relevant_ids: List[int]) -> float:
    total = 0.0
    for res, rel in zip(results, relevant_ids):
        if rel in res:
            total += 1.0 / (res.index(rel) + 1)
    return total / len(results) if results else 0.0


def evaluate_strategy(
    name: str,
    search_fn: Callable[[str], List[Document]],
    ground_truth: List[dict],
) -> dict:
    predicted_chunk_ids: List[List[int]] = []
    relevant_ids: List[int] = []

    for row in ground_truth:
        docs = search_fn(row["question"])
        predicted_chunk_ids.append([d.metadata.get("chunk_id") for d in docs])
        relevant_ids.append(int(row["chunk_id"]))

    return {
        "strategy": name,
        "hit_rate": round(hit_rate(predicted_chunk_ids, relevant_ids), 4),
        "mrr": round(mrr(predicted_chunk_ids, relevant_ids), 4),
        "n": len(ground_truth),
    }


def main():
    ground_truth = _load_ground_truth()

    chunks = load_and_split()
    embeddings = get_embeddings()
    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(PERSIST_DIR),
    )
    bm25_index = BM25Index.from_documents(chunks)
    hybrid_retriever = HybridRetriever(vectorstore, bm25_index)

    strategies = {
        "vector_only": lambda q: vectorstore.similarity_search(q, k=TOP_K),
        "bm25_only": lambda q: bm25_index.search(q, top_k=TOP_K),
        "hybrid_rrf": lambda q: hybrid_retriever.get_candidates(q)[:TOP_K],
        "hybrid_rrf_reranked": lambda q: rerank(
            q, hybrid_retriever.get_candidates(q), top_n=RERANK_TOP_N
        ),
    }

    results = [evaluate_strategy(name, fn, ground_truth) for name, fn in strategies.items()]

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        f.write("# Resultados de evaluación de retrieval\n\n")
        f.write(f"Dataset: {len(ground_truth)} preguntas (`ground_truth.csv`) · top_k={TOP_K}\n\n")
        f.write("| Estrategia | Hit Rate | MRR |\n|---|---|---|\n")
        for r in results:
            f.write(f"| {r['strategy']} | {r['hit_rate']} | {r['mrr']} |\n")

    print(f"\nResultados guardados en {RESULTS_PATH}\n")
    for r in results:
        print(f"{r['strategy']:22s} hit_rate={r['hit_rate']:.4f}  mrr={r['mrr']:.4f}")


if __name__ == "__main__":
    main()
