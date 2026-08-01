# bimbam-buy-ai-agent/rag/graph.py
import operator
from typing import Annotated, List, TypedDict, Dict, Any

from langchain_core.documents import Document
from langchain_core.messages import BaseMessage
from langgraph.graph import END, StateGraph

from rag.pipeline import get_pipeline

# Paso 1: Definir el estado del grafo
class AgentState(TypedDict):
    question: str
    session_id: str
    chat_history: Annotated[List[BaseMessage], operator.add]
    documents: List[Document]
    answer: str
    standalone_question: str
    sources: List[str]
    timings_ms: Dict[str, Any]

# Inicializamos el pipeline (asumiendo que ya está configurado)
pipeline = get_pipeline()

# Paso 2: Nodo 'retrieve'
def retrieve(state: AgentState):
    """Busca documentos relevantes usando el retriever del pipeline."""
    docs = pipeline.retriever.get_relevant_documents(state["question"])
    # Extraemos fuentes (asumiendo que están en metadata['source'])
    sources = list(set([doc.metadata.get("source", "unknown") for doc in docs]))
    return {"documents": docs, "sources": sources}

# Paso 3: Nodo 'generate'
def generate(state: AgentState):
    """Genera la respuesta usando el LLM y el contexto recuperado."""
    # Usamos el LLM del pipeline para redactar la respuesta con un tono más casual
    system_prompt = (
        "Sos un asistente de soporte amable y casual de BimBam Buy. "
        "Respondé de forma cercana y servicial usando únicamente el contexto proporcionado. "
        "Si no sabés la respuesta, decilo con buena onda."
    )
    
    response = pipeline.llm.invoke(
        f"{system_prompt}\n\nContexto: {state['documents']}\n\nPregunta: {state['question']}"
    )
    
    return {
        "answer": response.content,
        "standalone_question": state["question"], # Simplificación inicial
        "timings_ms": {"total": 0} # Aquí podrías calcular el tiempo real si quisieras
    }

# Construcción del Grafo
def create_graph():
    workflow = StateGraph(AgentState)

    # Añadir nodos
    workflow.add_node("retrieve", retrieve)
    workflow.add_node("generate", generate)

    # Definir el flujo
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", END)

    return workflow.compile()
