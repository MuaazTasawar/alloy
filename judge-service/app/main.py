from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.judge import score_comparison, score_single_answer

app = FastAPI(title="Alloy Judge Service")


class SingleScoreRequest(BaseModel):
    question: str
    strategy: str
    answer: str


class SingleScoreResponse(BaseModel):
    score: float
    reasoning: str


class CompareRequest(BaseModel):
    question: str
    base_model_answer: str
    rag_answer: str
    finetuned_answer: str


@app.get("/health")
def health():
    return {"status": "ok", "service": "judge-service"}


@app.post("/score", response_model=SingleScoreResponse)
def score(request: SingleScoreRequest):
    try:
        result = score_single_answer(request.question, request.strategy, request.answer)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Judge scoring failed: {exc}")
    return SingleScoreResponse(**result)


@app.post("/compare")
def compare(request: CompareRequest):
    try:
        result = score_comparison(
            question=request.question,
            answer_a=request.base_model_answer,
            answer_b=request.rag_answer,
            answer_c=request.finetuned_answer,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Judge comparison failed: {exc}")
    return result