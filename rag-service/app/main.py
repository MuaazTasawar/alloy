import logging

from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.db import init_pool
from app.generation import generate_base_answer, generate_rag_answer
from app.ingest import ingest_document
from app.retrieval import build_context_block, retrieve_context

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rag-service")

app = FastAPI(title="Alloy RAG Service")

_ready = False


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


class BaseQueryRequest(BaseModel):
    question: str


class BaseQueryResponse(BaseModel):
    answer: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    cost_usd: float


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Anything not already turned into an HTTPException (a model load failure,
    # a malformed DB row, etc.) lands here instead of taking the process down
    # or leaking a raw traceback to the client.
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal error in rag-service"})


@app.on_event("startup")
def on_startup():
    global _ready
    try:
        init_pool()
        _ready = True
    except Exception:
        logger.exception("Failed to initialize database pool")
        _ready = False


@app.get("/health")
def health():
    return {"status": "ok", "service": "rag-service"}


@app.get("/ready")
def ready():
    """Separate from /health: reports whether the DB pool actually came up,
    so an orchestrator can distinguish 'process is alive' from 'can serve traffic'."""
    if not _ready:
        raise HTTPException(status_code=503, detail="rag-service is not ready")
    return {"status": "ready"}


@app.post("/ingest")
async def ingest(file: UploadFile):
    if not file.filename:
        raise HTTPException(status_code=400, detail="A filename is required")

    raw_bytes = await file.read()
    try:
        raw_text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 text")

    if not raw_text.strip():
        raise HTTPException(status_code=400, detail="File is empty")

    try:
        result = ingest_document(filename=file.filename, raw_text=raw_text)
    except Exception:
        logger.exception("Ingestion failed for %s", file.filename)
        raise HTTPException(status_code=500, detail="Failed to ingest document")

    return result


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="question must not be empty")

    try:
        chunks = retrieve_context(request.question, top_k=request.top_k)
        context = build_context_block(chunks)
        result = generate_rag_answer(request.question, context)
    except Exception:
        logger.exception("RAG query failed")
        raise HTTPException(status_code=500, detail="RAG generation failed")

    return QueryResponse(
        answer=result["answer"],
        latency_ms=result["latency_ms"],
        input_tokens=result["input_tokens"],
        output_tokens=result["output_tokens"],
        cost_usd=result["cost_usd"],
        sources=[c["filename"] for c in chunks],
    )


@app.post("/base-query", response_model=BaseQueryResponse)
def base_query(request: BaseQueryRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="question must not be empty")

    try:
        result = generate_base_answer(request.question)
    except Exception:
        logger.exception("Base model query failed")
        raise HTTPException(status_code=500, detail="Base model generation failed")

    return BaseQueryResponse(**result)