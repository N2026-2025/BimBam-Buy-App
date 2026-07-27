# test_rag.py
import os
import numpy as np
from google import genai
from embedder import Embedder

def main():
    # 1. Verificar la API Key de Google
    # Asegúrate de haber hecho: export GEMINI_API_KEY="tu_llave_aqui"
    if not os.environ.get("GEMINI_API_KEY"):
        print("❌ Error: La variable de entorno GEMINI_API_KEY no está configurada.")
        return

    print("🤖 Inicializando cliente de Google GenAI y Embedder ONNX...")
    ai_client = genai.Client()
    embedder = Embedder()

    # 2. Base de conocimientos de prueba (Simulando tu RAG)
    documents = [
        {
            "id": 1,
            "text": "Para el LLM Zoomcamp Challenge, la fecha límite de entrega es el próximo domingo a la medianoche. No se aceptan entregas tardías."
        },
        {
            "id": 2,
            "text": "Para instalar Docker en Windows, descarga Docker Desktop desde el sitio oficial y asegúrate de tener habilitado WSL2 en las características de Windows."
        },
        {
            "id": 3,
            "text": "La capa gratuita de Oracle Cloud (Always Free) te permite crear hasta dos bases de datos autónomas y usar instancias de cómputo Ampere ARM sin costo."
        }
    ]

    # 3. Vectorizar la base de conocimientos con ONNX
    print("📦 Indexando documentos localmente con ONNX...")
    texts_to_embed = [doc["text"] for doc in documents]
    doc_vectors = embedder.encode_batch(texts_to_embed) # Devuelve un array de NumPy

    # 4. Definir la consulta del usuario y vectorizarla
    query = "¿Cuándo tengo que entregar el desafío del Zoomcamp?"
    print(f"\n❓ Consulta del usuario: '{query}'")
    query_vector = embedder.encode(query)[0] # Tomamos el primer (y único) vector

    # 5. Recuperación (Retrieval) mediante producto punto
    # Como el embedder normaliza los vectores con norma L2, el producto punto es igual a la similitud de coseno
    scores = np.dot(doc_vectors, query_vector)
    best_idx = np.argmax(scores)
    context = documents[best_idx]["text"]
    
    print(f"🎯 Documento más relevante encontrado (Score: {scores[best_idx]:.4f}):")
    print(f"   '{context}'")

    # 6. Generación con Google Gemini
    print("\n🚀 Enviando contexto y pregunta a Gemini...")
    
    prompt = f"""
    Eres un asistente virtual para el bootcamp. Responde la pregunta del usuario utilizando únicamente el contexto provisto.
    Si no sabes la respuesta basándote en el contexto, di que no la encuentras.

    Contexto:
    {context}

    Pregunta:
    {query}

    Respuesta:
    """

    # Usamos el cliente moderno y el modelo recomendado para tareas rápidas y RAG
    response = ai_client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
    )

    print("\n✨ Respuesta final de Gemini:")
    print("-" * 50)
    print(response.text)
    print("-" * 50)

if __name__ == "__main__":
    main()
