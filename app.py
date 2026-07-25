"""
app.py
-----------------------------------------------------------------------------
API FastAPI del agente de soporte BimBam Buy.

Endpoints:
    GET  /health         -> chequeo simple del servicio
    POST /ask             -> recibe una pregunta y devuelve la respuesta del
                             agente RAG junto con las fuentes citadas

Ejecutar localmente:
    uvicorn app:app --reload --port 8000

La cadena RAG se construye una sola vez al iniciar el proceso (lifespan),
para no reconstruir el índice vectorial en cada request.
-----------------------------------------------------------------------------
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from rag_engine import get_qa_chain, answer_question

qa_chain = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global qa_chain
    qa_chain = get_qa_chain()
    yield


app = FastAPI(
    title="BimBam Buy AI Support Agent",
    description=(
        "Agente RAG desarrollado para el Challenge Agente IA de "
        "Alura + Oracle Next Education (ONE). Responde preguntas de "
        "soporte al cliente usando la documentación oficial de BimBam Buy."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, examples=["¿Cuánto tarda un reembolso?"])


class AskResponse(BaseModel):
    question: str
    answer: str
    sources: list[str]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/ready")
def health_ready():
    """Indica si el índice vectorial ya fue construido y el agente está listo."""
    if qa_chain is None:
        raise HTTPException(status_code=503, detail="El agente todavía no está listo")
    return {"status": "ready"}


@app.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest):
    if qa_chain is None:
        raise HTTPException(status_code=503, detail="El agente todavía no está listo")
    try:
        result = answer_question(payload.question, chain=qa_chain)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return result


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
