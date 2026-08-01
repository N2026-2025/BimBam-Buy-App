"""
rag/pipeline.py
-----------------------------------------------------------------------------
Pipeline RAG avanzado. Orquesta, en orden:

    1. Carga de documentos (con fallback OCR) -> rag/loaders.py
    2. Chunking
    3. Vector store (Chroma) + índice BM25
    4. Por pregunta:
        a. Contextualización multi-turno (rag/memory.py)
        b. Recuperación híbrida: BM25 + vectorial fusionados con RRF
           (rag/hybrid_search.py)
        c. Reranking con cross-encoder (rag/reranker.py)
        d. Generación de la respuesta con el LLM, citando fuentes
        e. Registro de la interacción para observabilidad
           (monitoring/logging_db.py)

Se expone como una clase (`RagPipeline`) en vez de una cadena declarativa de
LangChain porque el flujo tiene ramas explícitas (multi-turno, fusión,
rerank, logging) que conviene poder leer y debuggear paso a paso — más
"ingeniería" que "magia".
-----------------------------------------------------------------------------
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import List, Optional

from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter

from rag.config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    COLLECTION_NAME,
    DATA_DIR,
    EMBEDDINGS_MODEL,
    EMBEDDINGS_PROVIDER,
    LLM_MODEL,
    LLM_PROVIDER,
    PERSIST_DIR,
    RERANK_TOP_N,
)
from rag.hybrid_search import BM25Index, HybridRetriever
from rag.loaders import load_documents
from rag.memory import contextualize_question, memory_store
from rag.reranker import rerank

logger = logging.getLogger(__name__)

ANSWER_PROMPT = PromptTemplate(
    input_variables=["context", "question"],
    template="""Eres el agente de soporte al cliente de BimBam Buy, una tienda
de e-commerce en LATAM. Respondé SIEMPRE en español, con un tono cercano,
claro y profesional, igual que el de la marca.

Usá EXCLUSIVAMENTE la información del contexto para responder. Si la
respuesta no está en el contexto, decí explícitamente que no tenés esa
información y sugerí contactar al canal oficial de soporte. No inventes
plazos, montos ni políticas que no estén en el contexto.

Contexto:
{context}

Pregunta del cliente: {question}

Respuesta (clara, breve y accionable):""",
)


def get_embeddings():
    if EMBEDDINGS_PROVIDER == "openai":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(model=EMBEDDINGS_MODEL)
    if EMBEDDINGS_PROVIDER == "google":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        return GoogleGenerativeAIEmbeddings(model=EMBEDDINGS_MODEL)
    if EMBEDDINGS_PROVIDER == "cohere":
        from langchain_cohere import CohereEmbeddings
        return CohereEmbeddings(model=EMBEDDINGS_MODEL)
    if EMBEDDINGS_PROVIDER == "local":
        # Embeddings locales (ONNX, all-MiniLM-L6-v2), sin API externa.
        # Requiere haber corrido antes: python -m rag.local_embeddings.download
        from rag.embeddings_local import ONNXEmbeddings
        return ONNXEmbeddings()
    raise ValueError(f"EMBEDDINGS_PROVIDER no soportado: {EMBEDDINGS_PROVIDER}")


def load_and_split(data_dir: Path = DATA_DIR) -> List[Document]:
    """Carga los PDFs (con fallback OCR) y los trocea, asignando un
    `chunk_id` estable a cada fragmento en `metadata`. Se usa tanto en el
    pipeline principal como en `evaluation/` para que los ids sean
    consistentes entre la generación del ground truth y la evaluación.
    """
    documents = load_documents(data_dir)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(documents)
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = i
    return chunks


def get_llm(temperature: float = 0.2):
    if LLM_PROVIDER == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=LLM_MODEL, temperature=temperature)
    if LLM_PROVIDER == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=LLM_MODEL, temperature=temperature)
    if LLM_PROVIDER == "cohere":
        from langchain_cohere import ChatCohere
        return ChatCohere(model=LLM_MODEL, temperature=temperature)
    raise ValueError(f"LLM_PROVIDER no soportado: {LLM_PROVIDER}")


class RagPipeline:
    """Pipeline RAG completo: ingesta + retrieval híbrido + rerank + memoria."""

    def __init__(self):
        self.vectorstore: Optional[Chroma] = None
        self.bm25_index: Optional[BM25Index] = None
        self.hybrid_retriever: Optional[HybridRetriever] = None
        self.llm = get_llm()
        self._chunks: List[Document] = []

    # --------------------------------------------------------------- build --
    def build(self, data_dir: Path = DATA_DIR, force_rebuild: bool = False) -> "RagPipeline":
        embeddings = get_embeddings()

        reuse_existing = (
            PERSIST_DIR.exists() and any(PERSIST_DIR.iterdir()) and not force_rebuild
        )

        if reuse_existing:
            logger.info("Reutilizando índice vectorial existente en %s", PERSIST_DIR)
            self.vectorstore = Chroma(
                collection_name=COLLECTION_NAME,
                embedding_function=embeddings,
                persist_directory=str(PERSIST_DIR),
            )
            # BM25 necesita los chunks en memoria: los volvemos a leer/trocear.
            # (Es barato: no llama a ningún LLM ni API de embeddings).
            self._chunks = load_and_split(data_dir)
        else:
            logger.info("Construyendo índice vectorial desde cero...")
            self._chunks = load_and_split(data_dir)
            self.vectorstore = Chroma.from_documents(
                documents=self._chunks,
                embedding=embeddings,
                collection_name=COLLECTION_NAME,
                persist_directory=str(PERSIST_DIR),
            )
            self.vectorstore.persist()

        self.bm25_index = BM25Index.from_documents(self._chunks)
        self.hybrid_retriever = HybridRetriever(self.vectorstore, self.bm25_index)
        return self

    @staticmethod
    def _split(documents: List[Document]) -> List[Document]:
        """Alias de compatibilidad; preferí `load_and_split()` a nivel de
        módulo, que además asigna `chunk_id` estable para evaluación."""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        return splitter.split_documents(documents)

    # ---------------------------------------------------------------- ask --
    def ask(self, question: str, session_id: str = "default") -> dict:
        """Ejecuta el pipeline completo para una pregunta y devuelve un
        resultado enriquecido, listo para servir por API/UI y para loggear
        en el sistema de observabilidad.
        """
        if self.hybrid_retriever is None:
            raise RuntimeError("El pipeline no fue construido. Llamá a .build() primero.")

        t0 = time.perf_counter()

        # 1) Multi-turno: reformular la pregunta con el historial de la sesión
        standalone_question = contextualize_question(self.llm, session_id, question)
        t_contextualize = time.perf_counter()

        # 2) Recuperación híbrida (BM25 + vectorial, fusionados con RRF)
        candidates = self.hybrid_retriever.get_candidates(standalone_question)
        t_retrieve = time.perf_counter()

        # 3) Reranking con cross-encoder (precisión sobre el pool de stage 1)
        top_chunks = rerank(standalone_question, candidates, top_n=RERANK_TOP_N)
        t_rerank = time.perf_counter()

        # 4) Generación de la respuesta
        context = "\n\n---\n\n".join(
            f"[Fuente: {doc.metadata.get('source')} - pág. {doc.metadata.get('page')}]\n{doc.page_content}"
            for doc in top_chunks
        )
        prompt_text = ANSWER_PROMPT.format(context=context, question=standalone_question)
        response = self.llm.invoke(prompt_text)
        answer = response.content if hasattr(response, "content") else str(response)
        t_generate = time.perf_counter()

        # 5) Memoria: guardar el turno para futuras preguntas de la sesión
        memory_store.add_turn(session_id, question, answer)

        sources = sorted({doc.metadata.get("source", "desconocido") for doc in top_chunks})

        return {
            "session_id": session_id,
            "question": question,
            "standalone_question": standalone_question,
            "answer": answer,
            "sources": sources,
            "retrieved_chunks": [
                {
                    "source": doc.metadata.get("source"),
                    "page": doc.metadata.get("page"),
                    "rerank_score": doc.metadata.get("rerank_score"),
                    "preview": doc.page_content[:180],
                }
                for doc in top_chunks
            ],
            "timings_ms": {
                "contextualize": round((t_contextualize - t0) * 1000, 1),
                "hybrid_retrieval": round((t_retrieve - t_contextualize) * 1000, 1),
                "rerank": round((t_rerank - t_retrieve) * 1000, 1),
                "generation": round((t_generate - t_rerank) * 1000, 1),
                "total": round((t_generate - t0) * 1000, 1),
            },
        }


_pipeline: Optional[RagPipeline] = None


def get_pipeline(force_rebuild: bool = False) -> RagPipeline:
    """Devuelve un singleton del pipeline ya construido (carga perezosa)."""
    global _pipeline
    if _pipeline is None:
        _pipeline = RagPipeline().build(force_rebuild=force_rebuild)
    return _pipeline
