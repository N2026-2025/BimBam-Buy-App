"""
evaluation/evaluate_answers.py
-----------------------------------------------------------------------------
Evalúa la calidad de las respuestas GENERADAS (no solo del retrieval),
combinando dos técnicas de llm-zoomcamp 04-evaluation:

    1. LLM-as-a-judge: un segundo LLM (el "juez") clasifica cada respuesta
       como RELEVANT / PARTLY_RELEVANT / NON_RELEVANT respecto a la
       pregunta, con una breve explicación.
    2. Cosine similarity: se embeben la pregunta y la respuesta y se mide
       la similaridad coseno entre ambos vectores, como métrica automática
       barata y reproducible que no depende de otra llamada a un LLM.

Corre el pipeline completo (hybrid search + rerank + generación) sobre una
muestra del `ground_truth.csv` y guarda un CSV con los resultados más un
resumen de la distribución de relevancia.

Uso:
    python -m evaluation.evaluate_answers --sample-size 30
-----------------------------------------------------------------------------
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path

import numpy as np

from rag.pipeline import get_embeddings, get_llm, get_pipeline

GROUND_TRUTH_PATH = Path(__file__).resolve().parent / "ground_truth.csv"
RESULTS_PATH = Path(__file__).resolve().parent / "results" / "answer_quality.csv"

JUDGE_PROMPT = """Sos un evaluador de calidad de respuestas de un agente de
soporte al cliente. Te paso una PREGUNTA y la RESPUESTA que dio el agente.
Clasificá la respuesta como una de estas tres opciones:

- "RELEVANT": responde correctamente y de forma completa la pregunta.
- "PARTLY_RELEVANT": responde parcialmente, o se relaciona pero le falta
  precisión o algún dato importante.
- "NON_RELEVANT": no responde la pregunta, es genérica o está desviada.

Pregunta: {question}
Respuesta del agente: {answer}

Respondé ÚNICAMENTE con un JSON de la forma:
{{"relevance": "RELEVANT" | "PARTLY_RELEVANT" | "NON_RELEVANT", "explanation": "..."}}"""


def cosine_similarity(a: list[float], b: list[float]) -> float:
    a, b = np.array(a), np.array(b)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom else 0.0


def judge_answer(llm, question: str, answer: str) -> dict:
    prompt = JUDGE_PROMPT.format(question=question, answer=answer)
    response = llm.invoke(prompt)
    text = response.content.strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"relevance": "UNKNOWN", "explanation": text[:200]}


def main(sample_size: int = 30, seed: int = 42):
    with open(GROUND_TRUTH_PATH, encoding="utf-8") as f:
        ground_truth = list(csv.DictReader(f))

    random.seed(seed)
    sample = random.sample(ground_truth, min(sample_size, len(ground_truth)))

    pipeline = get_pipeline()
    judge_llm = get_llm(temperature=0.0)
    embeddings = get_embeddings()

    rows = []
    for row in sample:
        result = pipeline.ask(row["question"], session_id=f"eval-{row['chunk_id']}")
        judgement = judge_answer(judge_llm, row["question"], result["answer"])

        q_emb = embeddings.embed_query(row["question"])
        a_emb = embeddings.embed_query(result["answer"])
        sim = cosine_similarity(q_emb, a_emb)

        rows.append(
            {
                "question": row["question"],
                "expected_source": row["source"],
                "answer": result["answer"],
                "sources_used": ";".join(result["sources"]),
                "relevance": judgement.get("relevance"),
                "explanation": judgement.get("explanation"),
                "cosine_similarity": round(sim, 4),
                "latency_ms": result["timings_ms"]["total"],
            }
        )

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    # Resumen de distribución de relevancia (como en llm-zoomcamp 04-evaluation)
    total = len(rows)
    counts = {}
    for r in rows:
        counts[r["relevance"]] = counts.get(r["relevance"], 0) + 1

    print(f"\nResultados guardados en {RESULTS_PATH}\n")
    print("Distribución de relevancia (LLM-as-judge):")
    for label, count in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {label:20s} {count:3d}  ({100 * count / total:.1f}%)")

    avg_sim = sum(r["cosine_similarity"] for r in rows) / total
    avg_latency = sum(r["latency_ms"] for r in rows) / total
    print(f"\nSimilaridad coseno promedio (pregunta vs. respuesta): {avg_sim:.4f}")
    print(f"Latencia promedio del pipeline: {avg_latency:.1f} ms")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-size", type=int, default=30)
    args = parser.parse_args()
    main(sample_size=args.sample_size)
