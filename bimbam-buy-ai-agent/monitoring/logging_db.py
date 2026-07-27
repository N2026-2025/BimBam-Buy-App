"""
monitoring/logging_db.py
-----------------------------------------------------------------------------
Registro de interacciones para observabilidad, siguiendo el patrón de
llm-zoomcamp 05-monitoring: cada pregunta/respuesta se guarda en una base de
datos (por defecto SQLite local; en producción, Postgres — ver
`MONITORING_DB_URL` en `.env` y el servicio `postgres` en
`docker-compose.monitoring.yml`) junto con:

    - la pregunta original y la reformulada (standalone question)
    - la respuesta y las fuentes citadas
    - tiempos de cada etapa del pipeline (contextualización, retrieval,
      rerank, generación)
    - feedback del usuario (👍/👎), para poder auditar calidad en el tiempo

Grafana se conecta a esta misma base para armar el dashboard de monitoreo
(ver `monitoring/grafana/`).
-----------------------------------------------------------------------------
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker

from rag.config import MONITORING_DB_URL

Base = declarative_base()


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    session_id = Column(String(64), index=True)
    question = Column(Text)
    standalone_question = Column(Text)
    answer = Column(Text)
    sources = Column(Text)          # JSON list
    retrieved_chunks = Column(Text)  # JSON list (con rerank_score, útil para debugging)
    latency_contextualize_ms = Column(Float)
    latency_retrieval_ms = Column(Float)
    latency_rerank_ms = Column(Float)
    latency_generation_ms = Column(Float)
    latency_total_ms = Column(Float)
    feedback = Column(Integer, nullable=True)  # 1 = útil, -1 = no útil, None = sin feedback
    relevance = Column(String(32), nullable=True)  # completado por el pipeline de evaluación


_engine = create_engine(MONITORING_DB_URL, connect_args=(
    {"check_same_thread": False} if MONITORING_DB_URL.startswith("sqlite") else {}
))
Base.metadata.create_all(_engine)
_SessionLocal = sessionmaker(bind=_engine)


def log_interaction(result: dict) -> int:
    """Guarda el resultado de `RagPipeline.ask()` y devuelve el id generado."""
    timings = result.get("timings_ms", {})
    with _SessionLocal() as db:
        row = Interaction(
            session_id=result.get("session_id"),
            question=result.get("question"),
            standalone_question=result.get("standalone_question"),
            answer=result.get("answer"),
            sources=json.dumps(result.get("sources", []), ensure_ascii=False),
            retrieved_chunks=json.dumps(result.get("retrieved_chunks", []), ensure_ascii=False),
            latency_contextualize_ms=timings.get("contextualize"),
            latency_retrieval_ms=timings.get("hybrid_retrieval"),
            latency_rerank_ms=timings.get("rerank"),
            latency_generation_ms=timings.get("generation"),
            latency_total_ms=timings.get("total"),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row.id


def save_feedback(interaction_id: int, feedback: int) -> None:
    """feedback: 1 (👍 útil) o -1 (👎 no útil)."""
    with _SessionLocal() as db:
        row = db.get(Interaction, interaction_id)
        if row is not None:
            row.feedback = feedback
            db.commit()


def get_stats() -> dict:
    """Métricas agregadas simples para exponer en `/metrics` o dashboards."""
    with _SessionLocal() as db:
        total = db.query(Interaction).count()
        thumbs_up = db.query(Interaction).filter(Interaction.feedback == 1).count()
        thumbs_down = db.query(Interaction).filter(Interaction.feedback == -1).count()
        avg_latency = db.query(Interaction).with_entities(Interaction.latency_total_ms).all()
        avg_latency_ms = (
            sum(v[0] for v in avg_latency if v[0] is not None) / len(avg_latency)
            if avg_latency
            else 0.0
        )
    return {
        "total_interactions": total,
        "thumbs_up": thumbs_up,
        "thumbs_down": thumbs_down,
        "avg_latency_ms": round(avg_latency_ms, 1),
    }
