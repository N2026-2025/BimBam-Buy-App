"""
rag_engine.py
-----------------------------------------------------------------------------
Núcleo RAG (Retrieval-Augmented Generation) del agente de soporte de
BimBam Buy.

Responsabilidades:
    1. Cargar los documentos PDF de la carpeta `data/` (base de conocimiento).
    2. Dividirlos en fragmentos (chunks) manejables.
    3. Generar embeddings y guardarlos/leerlos de una base vectorial Chroma.
    4. Construir una cadena de RetrievalQA que responde preguntas citando
       la fuente (nombre del documento) usada para generar la respuesta.

Este módulo es agnóstico de interfaz: tanto `app.py` (FastAPI), `cli.py`
(terminal) como `streamlit_app.py` importan `get_qa_chain()` /
`answer_question()` desde aquí.

Proveedor de LLM y de embeddings configurable por variables de entorno,
para poder alternar entre OpenAI (ChatGPT), Google (Gemini/Gemma) o Cohere
sin tocar el resto del código.
-----------------------------------------------------------------------------
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document

load_dotenv()

# --------------------------------------------------------------------------- #
# Configuración general (editable vía variables de entorno / archivo .env)
# --------------------------------------------------------------------------- #
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
PERSIST_DIR = Path(os.getenv("CHROMA_PERSIST_DIR", BASE_DIR / "chroma_db"))
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "bimbam_buy_kb")

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))
RETRIEVER_K = int(os.getenv("RETRIEVER_K", "4"))

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()  # openai | google | cohere
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
EMBEDDINGS_PROVIDER = os.getenv("EMBEDDINGS_PROVIDER", LLM_PROVIDER).lower()

SYSTEM_PROMPT = """Eres el agente de soporte al cliente de BimBam Buy, una tienda
de e-commerce en LATAM. Respondé SIEMPRE en español, con un tono cercano, claro
y profesional, igual que el de la marca.

Usá EXCLUSIVAMENTE la información del contexto para responder. Si la
respuesta no está en el contexto, decí explícitamente que no tenés esa
información y sugerí contactar al canal oficial de soporte. No inventes
plazos, montos ni políticas que no estén en el contexto.

Contexto:
{context}

Pregunta del cliente: {question}

Respuesta (clara, breve y accionable):"""


# --------------------------------------------------------------------------- #
# Carga y troceado de documentos
# --------------------------------------------------------------------------- #
def load_documents(data_dir: Path = DATA_DIR) -> List[Document]:
    """Carga todos los PDF de `data_dir` usando PyPDFLoader.

    Cada Document conserva metadata `source` (nombre de archivo) y `page`,
    lo que permite citar la fuente exacta en cada respuesta.
    """
    pdf_paths = sorted(data_dir.glob("*.pdf"))
    if not pdf_paths:
        raise FileNotFoundError(
            f"No se encontraron archivos PDF en {data_dir}. "
            "Colocá la base de conocimiento (PDFs) en esa carpeta."
        )

    documents: List[Document] = []
    for pdf_path in pdf_paths:
        loader = PyPDFLoader(str(pdf_path))
        pages = loader.load()
        for page in pages:
            page.metadata["source"] = pdf_path.name
        documents.extend(pages)

    return documents


def split_documents(documents: List[Document]) -> List[Document]:
    """Divide los documentos en chunks con superposición para preservar contexto."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_documents(documents)


# --------------------------------------------------------------------------- #
# Embeddings / LLM (proveedor configurable)
# --------------------------------------------------------------------------- #
def get_embeddings():
    if EMBEDDINGS_PROVIDER == "openai":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(model=os.getenv("EMBEDDINGS_MODEL", "text-embedding-3-small"))
    if EMBEDDINGS_PROVIDER == "google":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        return GoogleGenerativeAIEmbeddings(model=os.getenv("EMBEDDINGS_MODEL", "models/embedding-001"))
    if EMBEDDINGS_PROVIDER == "cohere":
        from langchain_cohere import CohereEmbeddings
        return CohereEmbeddings(model=os.getenv("EMBEDDINGS_MODEL", "embed-multilingual-v3.0"))
    raise ValueError(f"EMBEDDINGS_PROVIDER no soportado: {EMBEDDINGS_PROVIDER}")


def get_llm():
    if LLM_PROVIDER == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=LLM_MODEL, temperature=0.2)
    if LLM_PROVIDER == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        # Compatible con modelos Gemini / Gemma servidos por Google AI Studio
        return ChatGoogleGenerativeAI(model=LLM_MODEL, temperature=0.2)
    if LLM_PROVIDER == "cohere":
        from langchain_cohere import ChatCohere
        return ChatCohere(model=LLM_MODEL, temperature=0.2)
    raise ValueError(f"LLM_PROVIDER no soportado: {LLM_PROVIDER}")


# --------------------------------------------------------------------------- #
# Vector store (Chroma) — construcción o carga desde disco
# --------------------------------------------------------------------------- #
def build_vectorstore(force_rebuild: bool = False) -> Chroma:
    """Crea (o reutiliza si ya existe) la base vectorial persistida en disco."""
    embeddings = get_embeddings()

    if PERSIST_DIR.exists() and any(PERSIST_DIR.iterdir()) and not force_rebuild:
        return Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=str(PERSIST_DIR),
        )

    documents = load_documents()
    chunks = split_documents(documents)

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=str(PERSIST_DIR),
    )
    vectorstore.persist()
    return vectorstore


# --------------------------------------------------------------------------- #
# Cadena de RetrievalQA
# --------------------------------------------------------------------------- #
def get_qa_chain(force_rebuild: bool = False) -> RetrievalQA:
    vectorstore = build_vectorstore(force_rebuild=force_rebuild)
    retriever = vectorstore.as_retriever(search_kwargs={"k": RETRIEVER_K})

    prompt = PromptTemplate(
        template=SYSTEM_PROMPT,
        input_variables=["context", "question"],
    )

    chain = RetrievalQA.from_chain_type(
        llm=get_llm(),
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt},
    )
    return chain


def answer_question(question: str, chain: RetrievalQA | None = None) -> dict:
    """Ejecuta la cadena RAG y devuelve la respuesta junto con las fuentes citadas."""
    chain = chain or get_qa_chain()
    result = chain.invoke({"query": question})

    sources = sorted({doc.metadata.get("source", "desconocido") for doc in result["source_documents"]})

    return {
        "question": question,
        "answer": result["result"],
        "sources": sources,
    }


if __name__ == "__main__":
    # Ejecutar `python rag_engine.py` construye/actualiza el índice vectorial.
    print("Construyendo la base vectorial a partir de los PDFs en 'data/'...")
    build_vectorstore(force_rebuild=True)
    print(f"Listo. Índice persistido en: {PERSIST_DIR}")
