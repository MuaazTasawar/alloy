from fastapi import FastAPI, HTTPException, UploadFile
from pydantic import BaseModel

from app.db import init_pool
from app.generation import generate_rag_answer
from app.ingest import ingest_document
from app.retrieval import build_context_block, retrieve_context

app = FastAPI(title="Alloy RAG Service")


class QueryRequest(BaseModel):
    question: str
    top_k: int | None = None


class QueryResponse(BaseModel):
    answer: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    cost_usd: float
    sources: list[str]


@app.on_event("startup")
def on_startup():
    init_pool()


@app.get("/health")
def health():
    return {"status": "ok", "service": "rag-service"}


@app.post("/ingest")
async def ingest(file: UploadFile):
    if not file.filename:
        raise HTTPException(status_code=400, detail="A filename is required")

    raw_bytes = await file.read()
    try:
        raw_text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 text")

    result = ingest_document(filename=file.filename, raw_text=raw_text)
    return result


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    chunks = retrieve_context(request.question, top_k=request.top_k)
    context = build_context_block(chunks)
    result = generate_rag_answer(request.question, context)

    return QueryResponse(
        answer=result["answer"],
        latency_ms=result["latency_ms"],
        input_tokens=result["input_tokens"],
        output_tokens=result["output_tokens"],
        cost_usd=result["cost_usd"],
        sources=[c["filename"] for c in chunks],
    )