from fastapi import FastAPI
from pydantic import BaseModel
from redis import Redis
from rq import Queue
from rq.job import Job

from app.config import get_settings
from app.data_gen import generate_synthetic_dataset
from app.inference import generate_finetuned_answer
from app.train import run_finetune_job

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


@app.get("/health")
def health():
    return {"status": "ok", "service": "finetune-service"}


@app.post("/generate-data")
def generate_data():
    """Kicks off synthetic Q&A pair generation from all ingested documents."""
    return generate_synthetic_dataset()


@app.post("/train")
def train():
    """Enqueues a LoRA fine-tune job on Redis/RQ — training itself may take a while,
    so this returns immediately with a job id to poll."""
    job = job_queue.enqueue(run_finetune_job, job_timeout="2h")
    return {"job_id": job.id, "status": "queued"}


@app.get("/train/status/{job_id}")
def train_status(job_id: str):
    job = Job.fetch(job_id, connection=redis_conn)
    return {
        "job_id": job.id,
        "status": job.get_status(),
        "result": job.result if job.is_finished else None,
    }


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    result = generate_finetuned_answer(request.question)
    return QueryResponse(**result)