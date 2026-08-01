# 🤖 BimBam Buy AI Support Agent

Agente RAG (Retrieval-Augmented Generation) **avanzado**, desarrollado para el
LLM ZOOMCAMP. 

Responde preguntas de soporte al cliente usando la documentación oficial de
la empresa (PDFs, con soporte OCR para escaneados), combinando **búsqueda
híbrida** (keywords + semántica) con **reranking**, **memoria conversacional
multi-turno**, una **interfaz de voz**, un **pipeline de evaluación** y un
**stack de monitoreo/observabilidad** completo — siguiendo los patrones
enseñados en [DataTalksClub/llm-zoomcamp](https://github.com/DataTalksClub/llm-zoomcamp).

---

## 📑 Índice

- [Sobre el proyecto](#-sobre-el-proyecto)
- [Objetivos del challenge](#-objetivos-del-challenge)
- [Arquitectura](#-arquitectura)
- [Capacidades avanzadas](#-capacidades-avanzadas)
- [Tecnologías](#-tecnologías)
- [Base de conocimiento](#-base-de-conocimiento)
- [Instrucciones para ejecutar el proyecto](#-instrucciones-para-ejecutar-el-proyecto)
- [Evaluación](#-evaluación)
- [Monitoreo y observabilidad](#-monitoreo-y-observabilidad)
- [Interfaz de voz](#-interfaz-de-voz)
- [Ejemplos de preguntas](#-ejemplos-de-preguntas)
- [Ejemplos de respuestas](#-ejemplos-de-respuestas)
- [Deploy en Oracle Cloud Infrastructure](#️-deploy-en-oracle-cloud-infrastructure-oci)
- [Estructura del repositorio](#-estructura-del-repositorio)
- [Mejoras futuras](#-mejoras-futuras)
- [Challenge Alura + ONE](#-challenge-alura--one)

---

## 📌 Sobre el proyecto

**BimBam Buy** es una tienda de e-commerce ficticia que opera en LATAM. Su
equipo de soporte necesita responder preguntas frecuentes sobre envíos,
pagos, garantías, devoluciones y el programa de afiliados de forma rápida,
consistente y trazable. Este agente resuelve ese problema con un pipeline
RAG de nivel productivo, no solo un demo de "pregunta-respuesta".

## 🎯 Objetivos del challenge

- ✔ Leer documentos de negocio (PDF, incluyendo escaneados vía OCR)
- ✔ Indexar la información (vectorial + keywords)
- ✔ Recuperar contenido relevante con alta precisión (hybrid search + rerank)
- ✔ Generar respuestas contextuales y conversacionales con un LLM
- ✔ Evaluar la calidad del sistema de forma objetiva y reproducible
- ✔ Monitorear el sistema en producción
- ✔ Desplegar la aplicación en Oracle Cloud Infrastructure (OCI)
- ✔ Publicar el proyecto completo en GitHub

## 🏗️ Arquitectura

Diagrama completo en [`architecture.mmd`](./architecture.mmd) (Mermaid).
Vista resumida del flujo por pregunta:

```mermaid
flowchart LR
    User(["🧑 Usuario"]) -->|texto o audio| Interfaces["FastAPI / Streamlit / CLI"]
    Interfaces --> Ctx["Contextualización<br/>(memoria multi-turno)"]
    Ctx --> Hybrid["Hybrid Search<br/>(BM25 + vectorial, fusión RRF)"]
    Hybrid --> Rerank["Cross-Encoder Reranking"]
    Rerank --> LLM["LLM<br/>(ChatGPT / Gemini-Gemma / Cohere)"]
    LLM -->|respuesta + fuentes| Interfaces
    Interfaces --> Log["Logging<br/>(Postgres/SQLite + Prometheus)"]
```

## ✨ Capacidades avanzadas

Esta versión extiende el MVP inicial con 7 capacidades adicionales de nivel
"AI engineer", cada una siguiendo un módulo específico de llm-zoomcamp:

### 1. Recuperación multi-documento con re-ranking

`rag/hybrid_search.py` + `rag/reranker.py`

Pipeline de dos etapas (patrón estándar de la industria):

- **Stage 1 (recall):** búsqueda BM25 (keywords) + búsqueda vectorial
  (embeddings), fusionadas con **Reciprocal Rank Fusion (RRF)** — evita el
  problema de mezclar escalas incompatibles (score BM25 vs. similaridad
  coseno), operando solo sobre las *posiciones* de cada ranking.
- **Stage 2 (precisión):** un **cross-encoder** multilingüe
  (`cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`) relee la pregunta y cada
  candidato juntos, y reordena por relevancia real antes de pasarlos al LLM.

### 2. Memoria conversacional (multi-turno)

`rag/memory.py`

Cada conversación tiene un `session_id`. Ante una pregunta de seguimiento
("¿y si pagué con transferencia?"), el LLM la reformula como una **pregunta
independiente** usando el historial reciente, antes de mandarla al
retriever — si no, el retriever buscaría con muy poca señal semántica.

### 3. Búsqueda híbrida (keyword + semántica)

`rag/hybrid_search.py`

Ver punto 1: BM25 resuelve bien coincidencias exactas (números de orden,
plazos como "48 horas", nombres de política), mientras que la búsqueda
vectorial resuelve paráfrasis y preguntas conceptuales. RRF combina lo
mejor de ambas sin necesidad de calibrar pesos.

### 4. Soporte OCR para documentos escaneados

`rag/loaders.py`

Si una página de un PDF no tiene suficiente texto extraíble (menos de
`OCR_MIN_CHARS_PER_PAGE`), se renderiza a imagen (`pdf2image`) y se le
aplica OCR (`pytesseract`, en español) automáticamente, sin intervención
manual. Útil para comprobantes, boletas o contratos escaneados.

### 5. Pipeline de evaluación de calidad de respuestas

`evaluation/`

Siguiendo llm-zoomcamp 04-evaluation:

- `generate_ground_truth.py`: le pide al LLM que genere preguntas
  realistas por cada chunk de la base de conocimiento (dataset
  pregunta → chunk esperado, sin armarlo a mano).
- `evaluate_retrieval.py`: mide **Hit Rate** y **MRR** comparando 4
  estrategias (solo vectorial, solo BM25, híbrida, híbrida + reranking).
- `evaluate_answers.py`: **LLM-as-a-judge** (clasifica cada respuesta como
  RELEVANT / PARTLY_RELEVANT / NON_RELEVANT) + **cosine similarity** entre
  pregunta y respuesta como métrica automática complementaria.

### 6. Monitoreo y observabilidad (logs, métricas, trazas)

`monitoring/`

Siguiendo llm-zoomcamp 05-monitoring:

- **Logging estructurado**: cada interacción (pregunta, pregunta
  reformulada, respuesta, fuentes, tiempos por etapa, feedback del usuario)
  se guarda en Postgres/SQLite (`monitoring/logging_db.py`).
- **Métricas Prometheus**: contadores de requests, latencia por etapa del
  pipeline (contextualización, retrieval, rerank, generación), feedback y
  errores, expuestos en `GET /metrics` (`monitoring/metrics.py`).
- **Dashboard Grafana** provisto (`monitoring/grafana/`), combinando
  métricas en vivo (Prometheus) con datos históricos (Postgres).

### 7. Interfaz de voz

`voice/`

`POST /voice/ask` recibe un audio, lo transcribe (Whisper), lo procesa con
el mismo pipeline RAG (hybrid search + rerank + memoria) y devuelve tanto
el texto como el audio de la respuesta sintetizado (TTS), en JSON con el
audio codificado en base64.

## 🛠️ Tecnologías

| Categoría               | Tecnología                                                      |
| ------------------------ | ---------------------------------------------------------------- |
| Lenguaje                 | Python                                                           |
| Orquestación RAG        | LangChain                                                        |
| Lectura de PDF           | PyPDF (`PyPDFLoader`)                                          |
| OCR                      | Tesseract (`pytesseract` + `pdf2image`)                      |
| Vector store             | ChromaDB                                                         |
| Búsqueda por keywords   | BM25 (`rank-bm25`)                                             |
| Reranking                | Cross-Encoder (`sentence-transformers`)                        |
| LLM / Embeddings         | ChatGPT (OpenAI), Gemini/Gemma (Google) o Cohere — configurable |
| Voz                      | Whisper (STT) + TTS de OpenAI                                    |
| API                      | FastAPI                                                          |
| UI                       | Streamlit                                                        |
| Logging de interacciones | SQLAlchemy (SQLite / Postgres)                                   |
| Métricas                | Prometheus                                                       |
| Dashboards               | Grafana                                                          |
| Contenedores             | Docker / Docker Compose                                          |
| Cloud                    | Oracle Cloud Infrastructure (OCI)                                |

## 📚 Base de conocimiento

| Archivo                                  | Contenido                                   |
| ---------------------------------------- | ------------------------------------------- |
| `politica_reembolsos_devoluciones.pdf` | Política de Reembolsos y Devoluciones      |
| `faq_metodos_pago.pdf`                 | Preguntas Frecuentes sobre Métodos de Pago |
| `manual_garantia_productos.pdf`        | Manual de Garantía de Productos            |
| `guia_tiempos_costos_envio.pdf`        | Guía de Tiempos y Costos de Envío         |
| `programa_afiliados.pdf`               | Programa de Afiliados                       |

## ⚙️ Instrucciones para ejecutar el proyecto

### 1. Cloná el repositorio y configurá el entorno

```bash
git clone https://github.com/<tu-usuario>/bimbam-buy-ai-agent.git
cd bimbam-buy-ai-agent
cp .env.example .env
# Completá la API key del proveedor elegido: OPENAI_API_KEY, GOOGLE_API_KEY o COHERE_API_KEY
```

### 2a. Ejecución local (sin Docker)

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Además de las dependencias de Python, instalar en el sistema:
#   Ubuntu/Debian: sudo apt install tesseract-ocr tesseract-ocr-spa poppler-utils
#   macOS:         brew install tesseract tesseract-lang poppler

# Construye el índice (vector store + BM25) a partir de los PDFs en data/
python rag_engine.py

# Levantar la API
uvicorn app:app --reload --port 8000

# (opcional) UI de chat
streamlit run streamlit_app.py

# (opcional) chat por consola, con memoria multi-turno
python cli.py
```

API disponible en `http://localhost:8000` (docs interactivas en `/docs`).

### 2b. Ejecución con Docker Compose

```bash
# Solo la app (API + UI)
docker compose up --build

# App + stack completo de monitoreo (Postgres + Prometheus + Grafana)
docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up --build
```

- API: `http://localhost:8000`
- UI (Streamlit): `http://localhost:8501`
- Grafana: `http://localhost:3000` (usuario/clave: `admin` / `admin`)
- Prometheus: `http://localhost:9090`

### 3. Probar la API

```bash
# Pregunta simple
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "¿Cuánto tarda un reembolso?"}'

# Pregunta de seguimiento (multi-turno, mismo session_id devuelto arriba)
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "¿Y si pagué con transferencia?", "session_id": "<session_id de la respuesta anterior>"}'

# Feedback sobre una respuesta
curl -X POST http://localhost:8000/feedback \
  -H "Content-Type: application/json" \
  -d '{"interaction_id": 1, "feedback": 1}'

# Pregunta por voz
curl -X POST http://localhost:8000/voice/ask \
  -F "audio=@pregunta.wav"
```

## 🧪 Evaluación

```bash
# 1. Generar el dataset de ground truth (preguntas sintéticas por chunk)
python -m evaluation.generate_ground_truth --n-per-chunk 3

# 2. Evaluar retrieval: Hit Rate y MRR de 4 estrategias
python -m evaluation.evaluate_retrieval
# -> evaluation/results/retrieval_metrics.md

# 3. Evaluar la calidad de las respuestas generadas (LLM-as-judge + cosine similarity)
python -m evaluation.evaluate_answers --sample-size 30
# -> evaluation/results/answer_quality.csv
```

## 📈 Monitoreo y observabilidad

Con el stack de monitoreo levantado (`docker-compose.monitoring.yml`):

- **Grafana** (`http://localhost:3000`) muestra: preguntas por minuto,
  latencia p95 total y por etapa del pipeline, errores, distribución de
  feedback (👍/👎) y estadísticas históricas desde Postgres.
- **Prometheus** (`http://localhost:9090`) scrapea `GET /metrics` de la API
  cada 15s.
- **`GET /stats`** devuelve un resumen rápido (total de interacciones,
  feedback, latencia promedio) sin necesidad de Grafana.

Para usar Postgres en vez de SQLite, en `.env`:

```bash
MONITORING_DB_URL=postgresql+psycopg2://bimbam:bimbam@postgres:5432/bimbam_monitoring
```

## 🎙️ Interfaz de voz

`POST /voice/ask` acepta un archivo de audio (`multipart/form-data`, campo
`audio`) y devuelve JSON con:

```json
{
  "interaction_id": 12,
  "session_id": "sess-...",
  "question_transcribed": "¿cuánto tarda un reembolso?",
  "answer_text": "El reembolso se procesa entre 5 y 10 días hábiles...",
  "sources": ["politica_reembolsos_devoluciones.pdf"],
  "answer_audio_base64": "SUQzBAAAAAAA...",
  "audio_mime_type": "audio/mpeg",
  "total_latency_ms": 3120.4
}
```

> El audio va en base64 (no en headers HTTP) porque el texto de la
> respuesta en español (con tildes/ñ) no es seguro de transportar en
> headers HTTP estándar.

## ❓ Ejemplos de preguntas

- ¿Cuánto tarda en procesarse un reembolso?
- ¿Y si pagué con transferencia? *(seguimiento, multi-turno)*
- ¿Puedo devolver un producto después de 10 días?
- ¿Qué métodos de pago aceptan?
- ¿Qué cubre la garantía de los productos?
- Mi pedido está demorado, ¿qué hago?
- ¿Cómo se calcula la comisión de un afiliado si hay una devolución?

## 💬 Ejemplos de respuestas

Ver [`examples/sample_qa.md`](./examples/sample_qa.md) para el detalle
completo con fuentes citadas.

## ☁️ Deploy en Oracle Cloud Infrastructure (OCI)

La aplicación está empaquetada con Docker (`Dockerfile` /
`docker-compose.yml`) para desplegarse en una instancia de **OCI Compute**.

- **URL pública:** `<completar con la URL de la instancia de OCI>`
- **Captura de la aplicación en ejecución:** `<agregar screenshot>`
- **Información de la VM de OCI:** `<shape, región y sistema operativo utilizados>`

> Reemplazar esta sección con la evidencia real una vez completado el
> despliegue.

## 🗂️ Estructura del repositorio

```text
bimbam-buy-ai-agent/
├── app.py                       # API FastAPI (/ask, /feedback, /metrics, /voice/ask)
├── rag_engine.py                 # Wrapper de compatibilidad -> rag/pipeline.py
├── cli.py                        # Chat de terminal con memoria multi-turno
├── streamlit_app.py              # UI de chat en Streamlit (con feedback 👍/👎)
├── rag/
│   ├── config.py                  # Configuración centralizada
│   ├── loaders.py                 # Carga de PDFs + fallback OCR
│   ├── hybrid_search.py           # BM25 + vectorial + Reciprocal Rank Fusion
│   ├── reranker.py                # Reranking con cross-encoder
│   ├── memory.py                  # Memoria multi-turno + contextualización
│   └── pipeline.py                # Orquestación end-to-end del pipeline RAG
├── monitoring/
│   ├── logging_db.py               # Logging de interacciones (SQLite/Postgres)
│   ├── metrics.py                  # Métricas Prometheus
│   ├── prometheus.yml              # Config de scraping
│   └── grafana/                    # Dashboard + datasources provisionados
├── evaluation/
│   ├── generate_ground_truth.py    # Dataset sintético de preguntas por chunk
│   ├── evaluate_retrieval.py       # Hit Rate / MRR (4 estrategias)
│   └── evaluate_answers.py         # LLM-as-judge + cosine similarity
├── voice/
│   ├── stt.py                       # Speech-to-Text (Whisper)
│   └── tts.py                       # Text-to-Speech
├── data/                            # Base de conocimiento (PDFs de BimBam Buy)
├── examples/
│   └── sample_qa.md                 # Ejemplos de preguntas y respuestas
├── architecture.mmd                 # Diagrama de arquitectura completo (Mermaid)
├── requirements.txt
├── Dockerfile
├── docker-compose.yml                # API + UI
├── docker-compose.monitoring.yml     # + Postgres + Prometheus + Grafana
├── .env.example
└── README.md
```

## 🚀 Mejoras futuras

- Query rewriting adicional para preguntas ambiguas (no solo multi-turno)
- Caché semántico de respuestas frecuentes
- Evaluación automática continua (correr `evaluation/` en cada release)
- Soporte de voz local/offline (faster-whisper + TTS local) para no depender de una API externa
- Trazas distribuidas (OpenTelemetry) además de métricas y logs
- Autenticación y rate limiting en la API

## 🏆 Proyecto

El objetivo es diseñar, implementar y desplegar un agente potenciado por IA capaz de
responder preguntas a partir de documentación de negocio, utilizando
técnicas modernas de IA Generativa y RAG. Esta versión extiende el MVP
inicial aplicando prácticas de ingeniería de IA de nivel productivo,
inspiradas en [DataTalksClub/llm-zoomcamp](https://github.com/DataTalksClub/llm-zoomcamp) (vector search, orquestación, evaluación, monitoreo y mejores prácticas de
RAG como hybrid search y reranking).
