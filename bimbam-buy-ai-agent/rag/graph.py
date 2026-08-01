# bimbam-buy-ai-agent/rag/graph.py
import operator
from typing import Annotated, List, TypedDict

from langchain_core.documents import Document
from langchain_core.messages import BaseMessage
from langgraph.graph import END, StateGraph

from rag.pipeline import get_pipeline

# Paso 1: Definir el estado del grafo
class AgentState(TypedDict):
    question: str
    chat_history: Annotated[List[BaseMessage], operator.add]
    documents: List[Document]
    answer: str

# Inicializamos el pipeline (asumiendo que ya está configurado)
pipeline = get_pipeline()

# Paso 2: Nodo 'retrieve'
def retrieve(state: AgentState):
    """Busca documentos relevantes usando el retriever del pipeline."""
    # Accedemos al retriever configurado en tu pipeline
    # Ajusta 'retriever' según la estructura interna de tu clase RagPipeline
    docs = pipeline.retriever.get_relevant_documents(state["question"])
    return {"documents": docs}

# Paso 3: Nodo 'generate'
def generate(state: AgentState):
    """Genera la respuesta usando el LLM y el contexto recuperado."""
    # Usamos el LLM del pipeline para redactar la respuesta
    # Asegúrate de que tu pipeline tenga acceso al LLM configurado
    response = pipeline.llm.invoke(
        f"Contexto: {state['documents']}\n\nPregunta: {state['question']}"
    )
    return {"answer": response.content}

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
