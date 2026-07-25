"""
cli.py
-----------------------------------------------------------------------------
Chat por terminal para probar el agente sin levantar la API ni la UI web.

Uso:
    python cli.py
-----------------------------------------------------------------------------
"""

from rag_engine import get_qa_chain, answer_question


def main():
    print("Construyendo/cargando el índice de conocimiento de BimBam Buy...")
    chain = get_qa_chain()
    print("Agente listo. Escribí tu pregunta (o 'salir' para terminar).\n")

    while True:
        question = input("Vos: ").strip()
        if question.lower() in {"salir", "exit", "quit"}:
            print("¡Hasta luego!")
            break
        if not question:
            continue

        result = answer_question(question, chain=chain)
        print(f"\nAgente: {result['answer']}")
        print(f"Fuentes: {', '.join(result['sources'])}\n")


if __name__ == "__main__":
    main()
