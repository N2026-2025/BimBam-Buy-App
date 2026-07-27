"""
monitoring/metrics.py
-----------------------------------------------------------------------------
Métricas Prometheus para observabilidad en tiempo real (complementa el log
en base de datos de `logging_db.py`, que es mejor para auditoría/BI, con
métricas agregadas listas para Grafana vía Prometheus).

Se expone como texto plano en `GET /metrics` (formato que Prometheus scrapea
directamente) y se agregan en `monitoring/prometheus.yml`.
-----------------------------------------------------------------------------
"""

from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

REQUESTS_TOTAL = Counter(
    "bimbam_agent_requests_total", "Cantidad total de preguntas recibidas", ["endpoint"]
)

REQUEST_LATENCY_SECONDS = Histogram(
    "bimbam_agent_request_latency_seconds",
    "Latencia total por request, en segundos",
    ["endpoint"],
    buckets=(0.25, 0.5, 1, 2, 3, 5, 8, 13, 21, 34),
)

STAGE_LATENCY_SECONDS = Histogram(
    "bimbam_agent_stage_latency_seconds",
    "Latencia por etapa del pipeline RAG, en segundos",
    ["stage"],  # contextualize | hybrid_retrieval | rerank | generation
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 3, 5, 8),
)

FEEDBACK_TOTAL = Counter(
    "bimbam_agent_feedback_total", "Feedback recibido del usuario", ["type"]  # up | down
)

ERRORS_TOTAL = Counter(
    "bimbam_agent_errors_total", "Errores del agente", ["endpoint"]
)


def record_result_metrics(endpoint: str, timings_ms: dict) -> None:
    for stage, value_ms in timings_ms.items():
        if stage == "total" or value_ms is None:
            continue
        STAGE_LATENCY_SECONDS.labels(stage=stage).observe(value_ms / 1000.0)
    if "total" in timings_ms and timings_ms["total"] is not None:
        REQUEST_LATENCY_SECONDS.labels(endpoint=endpoint).observe(timings_ms["total"] / 1000.0)


def metrics_response():
    """Devuelve (body, content_type) listos para una respuesta FastAPI."""
    return generate_latest(), CONTENT_TYPE_LATEST
