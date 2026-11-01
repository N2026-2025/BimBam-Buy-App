FROM python:3.11-slim

WORKDIR /app

# Dependencias del sistema:
#  - tesseract-ocr (+ paquete de idioma español): OCR de documentos escaneados
#  - poppler-utils: renderizado de páginas PDF a imagen (pdf2image)
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-spa \
        poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY bimbam-buy-ai-agent/requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY . .

# Hace importables rag, monitoring y voice desde la raíz de la app.
ENV PYTHONPATH=/app/bimbam-buy-ai-agent

EXPOSE 8000

# Al iniciar el contenedor, se construye/carga el índice y se levanta la API.
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
