import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from redis import Redis
from redis.exceptions import RedisError
from rq import Queue
from rq.job import Job

from app.config import get_settings
from app.data_gen import generate_synthetic_dataset
from app.inference import generate_finetuned_answer
from app.train import run_finetune_job

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("finetune-service")

settings = get_settings()

app = FastAPI(title="Alloy Fine-Tune Service")

redis_conn = Redis.from_url(settings.redis_url)
job_queue = Queue("finetune", connection=redis_conn)


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    answer: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    cost_usd: float


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal error in finetune-service"})


@app.get("/health")
def health():
    """Reports Redis connectivity too, since the training pipeline is useless
    without it even if the FastAPI process itself is up."""
    redis_ok = True
    try:
        redis_conn.ping()
    except RedisError:
        redis_ok = False

    return {"status": "ok" if redis_ok else "degraded", "service": "finetune-service", "redis_connected": redis_ok}


@app.post("/generate-data")
def generate_data():
    try:
        return generate_synthetic_dataset()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        logger.exception("Synthetic data generation failed")
        raise HTTPException(status_code=500, detail="Synthetic data generation failed")


@app.post("/train")
def train():
    try:
        redis_conn.ping()
    except RedisError:
        raise HTTPException(status_code=503, detail="Redis is unreachable — cannot queue training job")

    job = job_queue.enqueue(run_finetune_job, job_timeout="2h")
    return {"job_id": job.id, "status": "queued"}


@app.get("/train/status/{job_id}")
def train_status(job_id: str):
    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except Exception:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": job.id,
        "status": job.get_status(),
        "result": job.result if job.is_finished else None,
        "error": str(job.exc_info) if job.is_failed else None,
    }


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="question must not be empty")

    try:
        result = generate_finetuned_answer(request.question)
    except Exception:
        logger.exception("Fine-tuned model query failed")
        raise HTTPException(status_code=500, detail="Fine-tuned model generation failed")

    return QueryResponse(**result)