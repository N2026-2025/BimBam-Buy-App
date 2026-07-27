"""
evaluation/generate_ground_truth.py
-----------------------------------------------------------------------------
Genera un dataset de "ground truth" para evaluar retrieval y generación,
siguiendo el patrón de llm-zoomcamp 04-evaluation: por cada chunk de la base
de conocimiento, se le pide al LLM que genere preguntas que un cliente real
podría hacer y que se responden con ESE chunk específico.

Esto da un dataset (pregunta -> chunk_id esperado) sin necesidad de armarlo
a mano, útil para:
    - Medir Hit Rate / MRR de cada estrategia de retrieval
      (`evaluate_retrieval.py`)
    - Correr el pipeline completo y evaluar la respuesta final con
      LLM-as-judge (`evaluate_answers.py`)

Uso:
    python -m evaluation.generate_ground_truth --n-per-chunk 3
-----------------------------------------------------------------------------
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
from pathlib import Path

from rag.pipeline import get_llm, load_and_split

logger = logging.getLogger(__name__)

GROUND_TRUTH_PATH = Path(__file__).resolve().parent / "ground_truth.csv"

GENERATION_PROMPT = """Sos un cliente de BimBam Buy (tienda de e-commerce en LATAM).
A partir del siguiente fragmento de la documentación de soporte, generá {n}
preguntas realistas y variadas que un cliente podría escribirle al chat de
soporte y que se responden con la información de ESTE fragmento. No
inventes datos que no estén en el texto. Las preguntas deben poder
entenderse sin ver el fragmento (no digas "según el texto...").

Fragmento (fuente: {source}, página {page}):
\"\"\"
{content}
\"\"\"

Respondé ÚNICAMENTE con un array JSON de strings, por ejemplo:
["¿Pregunta 1?", "¿Pregunta 2?", "¿Pregunta 3?"]"""


def generate_ground_truth(n_per_chunk: int = 3, limit_chunks: int | None = None) -> None:
    chunks = load_and_split()

    if limit_chunks:
        chunks = chunks[:limit_chunks]

    llm = get_llm(temperature=0.7)

    rows = []
    for chunk in chunks:
        chunk_id = chunk.metadata["chunk_id"]
        prompt = GENERATION_PROMPT.format(
            n=n_per_chunk,
            source=chunk.metadata.get("source"),
            page=chunk.metadata.get("page"),
            content=chunk.page_content,
        )
        try:
            response = llm.invoke(prompt)
            text = response.content.strip()
            text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            questions = json.loads(text)
        except Exception:  # noqa: BLE001
            logger.exception("No se pudieron generar preguntas para el chunk %s", chunk_id)
            continue

        for question in questions:
            rows.append(
                {
                    "chunk_id": chunk_id,
                    "source": chunk.metadata.get("source"),
                    "page": chunk.metadata.get("page"),
                    "question": question,
                }
            )
        logger.info(
            "Chunk %s/%s -> %d preguntas generadas", chunk_id + 1, len(chunks), len(questions)
        )

    GROUND_TRUTH_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(GROUND_TRUTH_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["chunk_id", "source", "page", "question"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Ground truth generado: {len(rows)} preguntas -> {GROUND_TRUTH_PATH}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-per-chunk", type=int, default=3)
    parser.add_argument("--limit-chunks", type=int, default=None, help="Útil para pruebas rápidas/costos")
    args = parser.parse_args()
    generate_ground_truth(n_per_chunk=args.n_per_chunk, limit_chunks=args.limit_chunks)
