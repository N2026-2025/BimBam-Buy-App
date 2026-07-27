"""
cli.py
-----------------------------------------------------------------------------
Chat por terminal para probar el agente (pipeline avanzado: hybrid search +
reranking + memoria multi-turno) sin levantar la API ni la UI web.

Uso:
    python cli.py
-----------------------------------------------------------------------------
"""

from rag.pipeline import get_pipeline
from rag.memory import new_session_id
from rag_engine import answer_question


def main():
    print("Construyendo/cargando el índice de conocimiento de BimBam Buy...")
    pipeline = get_pipeline()
    session_id = new_session_id()
    print(f"Agente listo (sesión {session_id}). Escribí tu pregunta (o 'salir' para terminar).\n")

    while True:
        question = input("Vos: ").strip()
        if question.lower() in {"salir", "exit", "quit"}:
            print("¡Hasta luego!")
            break
        if not question:
            continue

        result = answer_question(question, session_id=session_id, pipeline=pipeline)
        print(f"\nAgente: {result['answer']}")
        print(f"Fuentes: {', '.join(result['sources'])}")
        print(
            f"(pregunta reformulada: \"{result['standalone_question']}\" · "
            f"{result['timings_ms']['total']} ms)\n"
        )


if __name__ == "__main__":
    main()
