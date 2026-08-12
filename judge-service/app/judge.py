import json

from anthropic import Anthropic

from app.config import get_settings

settings = get_settings()

JUDGE_PROMPT = """You are an impartial evaluator scoring an AI assistant's answer to a user's
question. Score strictly on: factual correctness, relevance to the question, and clarity.

Question: {question}

Answer to evaluate ({strategy}):
{answer}

Respond ONLY with JSON in this exact shape, no other text:
{{"score": <number 0-10, one decimal place>, "reasoning": "<one or two sentences explaining the score>"}}
"""

COMPARE_PROMPT = """You are an impartial evaluator comparing three AI-generated answers to the
same question, produced by different strategies. Score each independently on factual
correctness, relevance, and clarity, then say which one wins and why.

Question: {question}

Answer A (base_model):
{answer_a}

Answer B (rag):
{answer_b}

Answer C (finetuned):
{answer_c}

Respond ONLY with JSON in this exact shape, no other text:
{{
  "scores": {{
    "base_model": {{"score": <0-10>, "reasoning": "<why>"}},
    "rag": {{"score": <0-10>, "reasoning": "<why>"}},
    "finetuned": {{"score": <0-10>, "reasoning": "<why>"}}
  }},
  "winner": "<base_model|rag|finetuned>",
  "winner_reasoning": "<one or two sentences on why this strategy won overall>"
}}
"""


def _get_client() -> Anthropic:
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set — required for judge scoring")
    return Anthropic(api_key=settings.anthropic_api_key)


def _extract_json(response) -> dict:
    raw = "".join(block.text for block in response.content if block.type == "text")
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(raw)


def score_single_answer(question: str, strategy: str, answer: str) -> dict:
    client = _get_client()
    prompt = JUDGE_PROMPT.format(question=question, strategy=strategy, answer=answer)

    response = client.messages.create(
        model=settings.judge_model,
        max_tokens=settings.max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return _extract_json(response)


def score_comparison(question: str, answer_a: str, answer_b: str, answer_c: str) -> dict:
    """Scores base_model vs rag vs finetuned answers in a single judge call so the
    winner determination is consistent across all three, rather than three isolated calls."""
    client = _get_client()
    prompt = COMPARE_PROMPT.format(
        question=question, answer_a=answer_a, answer_b=answer_b, answer_c=answer_c
    )

    response = client.messages.create(
        model=settings.judge_model,
        max_tokens=settings.max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return _extract_json(response)