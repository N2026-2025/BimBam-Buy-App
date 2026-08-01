"""
rag/embeddings_local.py
-----------------------------------------------------------------------------
Adaptador de `rag/local_embeddings/embedder.py` (ONNX + all-MiniLM-L6-v2) a
la interfaz `Embeddings` de LangChain, para poder usarlo como un proveedor
más de `EMBEDDINGS_PROVIDER` (junto a openai / google / cohere) sin tocar
`Chroma.from_documents`, `similarity_search`, etc. — todos esperan un objeto
con `.embed_documents(list[str])` y `.embed_query(str)`.

Por qué embeddings locales:
    - Sin costo por token ni dependencia de una API externa para indexar/
      consultar (relevante para el volumen de un challenge/portfolio).
    - Reproducible: mismos vectores siempre, útil para `evaluation/`
      (comparar estrategias de retrieval sin que el proveedor cambie los
      resultados entre corridas).
    - Funciona 100% offline una vez descargado el modelo.

El modelo se descarga una sola vez con:
    python -m rag.local_embeddings.download
-----------------------------------------------------------------------------
"""

from __future__ import annotations

from functools import lru_cache
from typing import List

from langchain_core.embeddings import Embeddings

from rag.config import LOCAL_EMBEDDINGS_MODEL_PATH
from rag.local_embeddings.embedder import Embedder


@lru_cache(maxsize=1)
def _get_embedder() -> Embedder:
    """Carga el modelo ONNX una sola vez (cacheado), ya que instanciar la
    sesión de ONNX Runtime tiene costo y el modelo es stateless/thread-safe
    para inferencia.
    """
    return Embedder(path=LOCAL_EMBEDDINGS_MODEL_PATH)


class ONNXEmbeddings(Embeddings):
    """Embeddings locales (ONNX Runtime, all-MiniLM-L6-v2 por defecto),
    compatibles con la interfaz `Embeddings` de LangChain.
    """

    def __init__(self, batch_size: int = 32):
        self.batch_size = batch_size
        self._embedder = _get_embedder()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        vectors: List[List[float]] = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            batch_vectors = self._embedder.encode_batch(batch)
            vectors.extend(batch_vectors)
        return vectors

    def embed_query(self, text: str) -> List[float]:
        return self._embedder.encode(text)
