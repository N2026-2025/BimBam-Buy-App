"""
streamlit_app.py
-----------------------------------------------------------------------------
Interfaz web simple (Streamlit) para conversar con el agente de soporte de
BimBam Buy.

Ejecutar:
    streamlit run streamlit_app.py
-----------------------------------------------------------------------------
"""

import streamlit as st

from rag_engine import get_qa_chain, answer_question

st.set_page_config(page_title="BimBam Buy · Soporte AI", page_icon="🤖")

st.title("🤖 BimBam Buy AI Support Agent")
st.caption(
    "Agente RAG desarrollado para el Challenge Agente IA de "
    "Alura + Oracle Next Education (ONE)."
)


@st.cache_resource(show_spinner="Cargando base de conocimiento...")
def load_chain():
    return get_qa_chain()


chain = load_chain()

if "messages" not in st.session_state:
    st.session_state.messages = []

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
            result = answer_question(question, chain=chain)
        st.markdown(result["answer"])
        st.caption(f"📄 Fuentes: {', '.join(result['sources'])}")

    st.session_state.messages.append({"role": "assistant", "content": result["answer"]})
