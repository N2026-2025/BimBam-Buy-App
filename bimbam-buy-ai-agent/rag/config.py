"""
rag/config.py
-----------------------------------------------------------------------------
Configuración centralizada del pipeline RAG avanzado. Todo es sobreescribible
por variable de entorno / archivo .env para no tocar código en distintos
entornos (local, Docker, OCI).
-----------------------------------------------------------------------------
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Datos y vector store ---------------------------------------------------
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
PERSIST_DIR = Path(os.getenv("CHROMA_PERSIST_DIR", BASE_DIR / "chroma_db"))
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "bimbam_buy_kb")

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))

# --- Recuperación (retrieval) ------------------------------------------------
VECTOR_TOP_K = int(os.getenv("VECTOR_TOP_K", "10"))       # candidatos por búsqueda semántica
BM25_TOP_K = int(os.getenv("BM25_TOP_K", "10"))            # candidatos por búsqueda por keywords
RRF_K = int(os.getenv("RRF_K", "60"))                       # constante de amortiguación de RRF
RERANK_TOP_N = int(os.getenv("RERANK_TOP_N", "4"))          # candidatos finales tras reranking

# --- OCR ---------------------------------------------------------------------
OCR_MIN_CHARS_PER_PAGE = int(os.getenv("OCR_MIN_CHARS_PER_PAGE", "20"))
OCR_LANG = os.getenv("OCR_LANG", "spa")  # idioma de tesseract (español)

# --- LLM / Embeddings ---------------------------------------------------------
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
EMBEDDINGS_PROVIDER = os.getenv("EMBEDDINGS_PROVIDER", LLM_PROVIDER).lower()
EMBEDDINGS_MODEL = os.getenv("EMBEDDINGS_MODEL", "text-embedding-3-small")

# --- Embeddings locales (ONNX, sin API externa) -------------------------------
# Usados cuando EMBEDDINGS_PROVIDER=local. Ver rag/embeddings_local.py y
# rag/local_embeddings/ (download.py + embedder.py).
LOCAL_EMBEDDINGS_MODEL_REPO = os.getenv("LOCAL_EMBEDDINGS_MODEL_REPO", "Xenova/all-MiniLM-L6-v2")
LOCAL_EMBEDDINGS_MODEL_PATH = Path(
    os.getenv("LOCAL_EMBEDDINGS_MODEL_PATH", BASE_DIR / "models" / LOCAL_EMBEDDINGS_MODEL_REPO)
)

# Modelo de reranking (cross-encoder multilingüe, funciona bien en español)
RERANKER_MODEL = os.getenv(
    "RERANKER_MODEL", "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
)

# --- Memoria conversacional ---------------------------------------------------
MAX_HISTORY_TURNS = int(os.getenv("MAX_HISTORY_TURNS", "6"))

# --- Monitoreo -----------------------------------------------------------------
_MONITORING_DATA_DIR = BASE_DIR / "monitoring_data"
_MONITORING_DATA_DIR.mkdir(exist_ok=True)
MONITORING_DB_URL = (
    os.getenv("MONITORING_DB_URL", "").strip()
    or f"sqlite:///{_MONITORING_DATA_DIR / 'monitoring.db'}"
)

# --- Voz -------------------------------------------------------------------------
STT_MODEL = os.getenv("STT_MODEL", "whisper-1")
TTS_MODEL = os.getenv("TTS_MODEL", "tts-1")
TTS_VOICE = os.getenv("TTS_VOICE", "alloy")
