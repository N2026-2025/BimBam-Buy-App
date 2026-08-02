import os
import json
import time
from google import genai
import chromadb
from embedder import Embedder # Tu embedder ONNX local

def load_ground_truth(file_path):
    """Carga el archivo con las preguntas y respuestas correctas ideales."""
    if not os.path.exists(file_path):
        # Datos de prueba por defecto si el archivo JSON no existe todavía
        return [
            {
                "question": "¿Cuánto tiempo tengo para pedir un reembolso?",
                "expected_answer": "El cliente tiene un plazo de 30 días corridos.",
                "category": "devoluciones"
            },
            {
                "question": "¿Cómo se calcula la comisión de un afiliado si hay una devolución?",
                "expected_answer": "La comisión se descuenta automáticamente del saldo del afiliado.",
                "category": "afiliados"
            }
        ]
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def evaluate_agent():
    if not os.environ.get("GEMINI_API_KEY"):
        print("❌ Error: GEMINI_API_KEY no configurada.")
        return

    print("🚀 Inicializando componentes para la suite de pruebas...")
    ai_client = genai.Client()
    embedder = Embedder()
    
    # Conexión a la base de datos Chroma real de BimBam Buy
    chroma_client = chromadb.PersistentClient(path="bimbam-buy-ai-agent/chroma_db")
    collection = chroma_client.get_collection(name="bimbam_knowledge_base")

    # Cargar preguntas del ground truth
    ground_truth_path = "bimbam-buy-ai-agent/evaluation/ground_truth.json"
    test_cases = load_ground_truth(ground_truth_path)
    
    report_results = []
    total_latency = 0
    successful_tests = 0

    print(f"\n📊 Ejecutando {len(test_cases)} pruebas automatizadas sobre el agente...")

    for idx, case in enumerate(test_cases):
        query = case["question"]
        expected = case["expected_answer"]
        print(f"\n[Test {idx+1}/{len(test_cases)}] Categoría: {case['category']}")
        print(f"❓ Pregunta: {query}")

        # --- Métrica de Tiempo: Inicio ---
        start_time = time.time()

        # 1. Retrieval (Recuperación)
        query_vector = embedder.encode(query).tolist()
        results = collection.query(query_embeddings=[query_vector], n_results=2)
        context = "\n---\n".join(results['documents'][0]) if results['documents'] else ""

        # 2. Generation (Generación con Gemini 3.5 Flash-Lite)
        prompt = f"Usa el contexto para responder de forma concisa.\nContexto: {context}\nPregunta: {query}"
        
        failed = False
        error_message = ""
        try:
            response = ai_client.models.generate_content(
                model='gemini-3.5-flash-lite',
                contents=prompt,
            )
            generated_text = response.text
            successful_tests += 1
        except Exception as e:
            failed = True
            generated_text = ""
            error_message = str(e)

        # --- Métrica de Tiempo: Fin ---
        latency = time.time() - start_time
        total_latency += latency

        print(f"⏱️  Latencia: {latency:.2f} segundos")

        # Guardar el resultado individual de este caso de prueba
        report_results.append({
            "test_number": idx + 1,
            "category": case["category"],
            "question": query,
            "expected_answer": expected,
            "agent_response": generated_text,
            "latency_seconds": round(latency, 2),
            "failed": failed,
            "error_message": error_message
        })

    # Resumen general de la ejecución de la suite
    summary = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_questions_tested": len(test_cases),
        "successful_responses": successful_tests,
        "failed_responses": len(test_cases) - successful_tests,
        "average_latency_seconds": round(total_latency / len(test_cases), 2) if test_cases else 0,
        "details": report_results
    }

    # Exportar métricas automáticamente al JSON de reporte
    report_path = "bimbam-buy-ai-agent/evaluation/test_report.json"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=4, ensure_ascii=False)

    print("\n" + "="*50)
    print("✨ ¡Suite de pruebas completada con éxito!")
    print(f"📝 Reporte generado en: {report_path}")
    print(f"⏱️  Latencia promedio general: {summary['average_latency_seconds']}s")
    print("="*50)

if __name__ == "__main__":
    evaluate_agent()
