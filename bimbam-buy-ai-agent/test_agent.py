import os
import sys
import time
from pathlib import Path

# Aseguramos que el directorio del proyecto esté en el path para poder importar 'rag'
# Esto asume que ejecutás el script desde la carpeta 'bimbam-buy-ai-agent'
sys.path.append(str(Path(__file__).parent))

# Forzamos el uso de embeddings locales antes de que se cargue la configuración
os.environ["EMBEDDINGS_PROVIDER"] = "local"

from rag.pipeline import get_pipeline

def main():
    print("Inicializando el pipeline con embeddings locales...")
    
    # Esto carga el pipeline (singleton) y construye el índice si no existe
    pipeline = get_pipeline()

    pregunta = "¿Qué es BimBam Buy?"
    print(f"\nPregunta: {pregunta}")

    # Medimos el tiempo de ejecución de la consulta
    start_time = time.perf_counter()
    resultado = pipeline.ask(pregunta)
    end_time = time.perf_counter()

    print("-" * 40)
    print(f"Respuesta:\n{resultado['answer']}")
    print("-" * 40)
    print(f"Tiempo total de ejecución: {end_time - start_time:.2f} segundos")

if __name__ == "__main__":
    main()
