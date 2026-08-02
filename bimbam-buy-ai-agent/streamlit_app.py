"""
streamlit_app.py
-----------------------------------------------------------------------------
Interfaz web (Streamlit) para conversar con el agente de soporte de
BimBam Buy. Usa el pipeline avanzado: hybrid search + reranking + memoria
conversacional multi-turno (una sesión de Streamlit = una `session_id`).

Ejecutar:
    streamlit run streamlit_app.py
-----------------------------------------------------------------------------
"""

import streamlit as st
import os

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))

# Aseguramos que la API Key de Gemini esté disponible
os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY", "")
os.environ["LLM_MODEL"] = "gemini-3.1-flash-lite"

from rag.pipeline import get_pipeline
from rag.memory import new_session_id
from monitoring.logging_db import log_interaction, save_feedback

st.set_page_config(page_title="BimBam Buy · Soporte AI", page_icon="🤖")

st.title("🤖 BimBam Buy AI Support Agent")
st.caption(
    "Agente RAG avanzado (hybrid search + reranking + memoria multi-turno) "
)


@st.cache_resource(show_spinner="Cargando base de conocimiento (vector store + BM25)...")
def load_pipeline():
    return get_pipeline()


pipeline = load_pipeline()

if "session_id" not in st.session_state:
    st.session_state.session_id = new_session_id()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_interaction_id" not in st.session_state:
    st.session_state.last_interaction_id = None

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

question = st.chat_input("Escribí tu pregunta sobre envíos, pagos, garantía o devoluciones...")

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Buscando en la documentación..."):
            from rag.graph import graph
            state = graph.invoke({"question": question, "session_id": st.session_state.session_id})
        
        raw_answer = state.get("answer", "No pude generar una respuesta.")
        if isinstance(raw_answer, list) and len(raw_answer) > 0:
            # Buscamos el texto si viene estructurado como lista de diccionarios
            first_elem = raw_answer[0]
            final_answer = first_elem.get("text", str(first_elem)) if isinstance(first_elem, dict) else str(first_elem)
        else:
            final_answer = str(raw_answer)

        result = {
            "answer": final_answer,
            "standalone_question": state.get("standalone_question", question),
            "sources": ", ".join([doc.metadata.get("source", "Desconocido") for doc in state.get("documents", [])]),
            "timings_ms": state.get("timings_ms", {}),
            "retrieved_chunks": [doc.page_content for doc in state.get("documents", [])]
        }

        st.markdown(result["answer"])
        # Limpiamos espacios, eliminamos duplicados con set y ordenamos alfabéticamente
        raw_sources = [s.strip() for s in result["sources"].split(",") if s.strip()]
        unique_sources = ", ".join(sorted(list(set(raw_sources))))
        st.caption(f"📄 Fuentes: {unique_sources}")
        with st.expander("Detalle técnico (retrieval, timings)"):
            st.json(result["timings_ms"])
            st.write("Pregunta reformulada:", result["standalone_question"])
            st.json(result["retrieved_chunks"])

        interaction_id = log_interaction(result)
        st.session_state.last_interaction_id = interaction_id

        col1, col2 = st.columns(2)
        if col1.button("👍 Útil", key=f"up-{interaction_id}"):
            save_feedback(interaction_id, 1)
            st.success("¡Gracias por el feedback!")
        if col2.button("👎 No útil", key=f"down-{interaction_id}"):
            save_feedback(interaction_id, -1)
            st.info("Gracias, lo tenemos en cuenta.")

    st.session_state.messages.append({"role": "assistant", "content": result["answer"]})

with st.sidebar:
    st.subheader("Sesión")
    st.code(st.session_state.session_id)
    if st.button("Nueva conversación"):
        st.session_state.session_id = new_session_id()
        st.session_state.messages = []
        st.rerun()
