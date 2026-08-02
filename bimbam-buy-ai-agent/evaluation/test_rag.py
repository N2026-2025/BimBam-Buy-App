import os
import chromadb
from google import genai
from embedder import Embedder

def main():
    # Inicialización rápida de componentes básicos
    ai_client = genai.Client()
    embedder = Embedder()
    
    chroma_client = chromadb.PersistentClient(path="bimbam-buy-ai-agent/chroma_db")
    collection = chroma_client.get_collection(name="bimbam_knowledge_base")

    # Una sola pregunta de control técnico
    query = "¿Cuánto tiempo tengo para pedir un reembolso?"
    query_vector = embedder.encode(query).tolist() 

    # Verificar el paso del Retriever
    results = collection.query(query_embeddings=[query_vector], n_results=1)
    context = results['documents'][0][0] if results['documents'] else "Sin contexto"

    # Verificar el paso del Generador con Gemini 3.5 Flash-Lite
    response = ai_client.models.generate_content(
        model='gemini-3.5-flash-lite',
        contents=f"Contexto: {context}\nPregunta: {query}"
    )
    print(f"✅ Conexión RAG exitosa. Respuesta corta: {response.text[:50]}...")

if __name__ == "__main__":
    main()
