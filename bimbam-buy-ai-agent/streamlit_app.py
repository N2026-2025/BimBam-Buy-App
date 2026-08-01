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

from rag.pipeline import get_pipeline
from rag.memory import new_session_id
from rag_engine import answer_question
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
            result = answer_question(question, session_id=st.session_state.session_id, pipeline=pipeline)
        st.markdown(result["answer"])
        st.caption(f"📄 Fuentes: {', '.join(result['sources'])}")
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
