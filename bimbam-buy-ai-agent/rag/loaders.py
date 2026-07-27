"""
rag/loaders.py
-----------------------------------------------------------------------------
Carga de documentos con soporte OCR.

Un PDF "nativo" (texto seleccionable) se lee directamente con PyPDFLoader.
Un PDF "escaneado" (imagen sin capa de texto) devuelve páginas casi vacías
con PyPDFLoader; en ese caso se recurre a OCR (Tesseract) sobre el render de
la página para extraer el texto igual.

Esto resuelve el caso real de soporte: contratos firmados, boletas o
comprobantes escaneados que un cliente adjunta y que no tienen texto
embebido en el PDF.
-----------------------------------------------------------------------------
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document

from rag.config import DATA_DIR, OCR_MIN_CHARS_PER_PAGE, OCR_LANG

logger = logging.getLogger(__name__)


def _ocr_page(pdf_path: Path, page_number: int) -> str:
    """Renderiza una página del PDF a imagen y le aplica OCR con Tesseract.

    Requiere los binarios `poppler-utils` (para pdf2image) y `tesseract-ocr`
    instalados en el sistema (ver Dockerfile).
    """
    try:
        import pytesseract
        from pdf2image import convert_from_path
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "Para usar OCR instalá las dependencias: "
            "pip install pytesseract pdf2image  "
            "y los binarios poppler-utils + tesseract-ocr"
        ) from exc

    images = convert_from_path(
        str(pdf_path), first_page=page_number + 1, last_page=page_number + 1
    )
    if not images:
        return ""
    return pytesseract.image_to_string(images[0], lang=OCR_LANG)


def load_documents(data_dir: Path = DATA_DIR, use_ocr_fallback: bool = True) -> List[Document]:
    """Carga todos los PDF de `data_dir`, aplicando OCR automáticamente en las
    páginas que no tengan texto extraíble (documentos escaneados).

    Cada Document conserva metadata:
        - source: nombre del archivo
        - page: número de página
        - extraction_method: "text" | "ocr"
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

        for i, page in enumerate(pages):
            text = page.page_content or ""
            method = "text"

            if use_ocr_fallback and len(text.strip()) < OCR_MIN_CHARS_PER_PAGE:
                logger.info(
                    "Página %s de %s parece escaneada (solo %d chars). Aplicando OCR...",
                    i,
                    pdf_path.name,
                    len(text.strip()),
                )
                try:
                    ocr_text = _ocr_page(pdf_path, i)
                    if len(ocr_text.strip()) > len(text.strip()):
                        text = ocr_text
                        method = "ocr"
                except Exception:  # noqa: BLE001
                    logger.exception("OCR falló en %s página %s, se conserva el texto original", pdf_path.name, i)

            page.page_content = text
            page.metadata["source"] = pdf_path.name
            page.metadata["extraction_method"] = method
            documents.append(page)

    return documents
