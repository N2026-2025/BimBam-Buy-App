"""
rag/memory.py
-----------------------------------------------------------------------------
Memoria conversacional multi-turno.

Dos responsabilidades:

1. `ChatMemoryStore`: guarda el historial de mensajes por `session_id`
   (una conversación = una sesión). En este proyecto se implementa en
   memoria de proceso por simplicidad; en producción se reemplazaría por
   Redis o Postgres (la interfaz ya está pensada para eso: intercambiar la
   clase sin tocar el resto del pipeline).

2. `contextualize_question()`: reescribe la pregunta de seguimiento del
   usuario como una "pregunta independiente" (standalone question) usando
   el LLM y el historial reciente. Esto es clave para RAG multi-turno: si el
   usuario pregunta "¿y si pagué con transferencia?" después de haber
   preguntado por reembolsos, el retriever necesita algo como "¿Cuánto tarda
   un reembolso si pagué con transferencia?" para poder buscar bien — la
   pregunta corta sola no tiene suficiente señal semántica ni léxica.
-----------------------------------------------------------------------------
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate

from rag.config import MAX_HISTORY_TURNS

CONTEXTUALIZE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Dado el historial de la conversación y la última pregunta del "
            "usuario (que puede hacer referencia a mensajes anteriores), "
            "reformulá esa pregunta como una pregunta independiente y "
            "completa, que se pueda entender sin necesidad de leer el "
            "historial. NO respondas la pregunta, solo reformulala si hace "
            "falta; si ya es independiente, devolvela igual. Respondé "
            "únicamente con la pregunta reformulada, sin explicaciones.",
        ),
        ("placeholder", "{history}"),
        ("human", "{question}"),
    ]
)


@dataclass
class ChatMemoryStore:
    """Historial de conversación en memoria, indexado por session_id."""

    _sessions: Dict[str, List[BaseMessage]] = field(default_factory=lambda: defaultdict(list))

    def get_history(self, session_id: str) -> List[BaseMessage]:
        return self._sessions[session_id][-2 * MAX_HISTORY_TURNS :]

    def add_turn(self, session_id: str, question: str, answer: str) -> None:
        self._sessions[session_id].append(HumanMessage(content=question))
        self._sessions[session_id].append(AIMessage(content=answer))

    def clear(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)


# Instancia global compartida por la app (equivalente in-memory de una tabla
# `conversations` en Redis/Postgres).
memory_store = ChatMemoryStore()


def contextualize_question(llm, session_id: str, question: str) -> str:
    """Devuelve la pregunta reformulada como independiente del contexto previo.

    Si no hay historial (primer turno de la sesión), devuelve la pregunta
    original sin llamar al LLM (evita una llamada innecesaria).
    """
    history = memory_store.get_history(session_id)
    if not history:
        return question

    chain = CONTEXTUALIZE_PROMPT | llm
    result = chain.invoke({"history": history, "question": question})
    return result.content.strip()


def new_session_id() -> str:
    """Genera un id de sesión simple basado en timestamp + contador de proceso."""
    import uuid

    return f"sess-{uuid.uuid4().hex[:12]}-{int(time.time())}"
