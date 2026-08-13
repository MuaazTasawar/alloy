import time
from functools import lru_cache

from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

from app.config import get_settings

settings = get_settings()

RAG_PROMPT_TEMPLATE = """You are a helpful assistant answering questions using only the context below.
If the context doesn't contain the answer, say you don't know.

Context:
{context}

Question: {question}

Answer:"""

BASE_PROMPT_TEMPLATE = """You are a helpful assistant. Answer the question as best you can.

Question: {question}

Answer:"""


@lru_cache
def get_generator():
    tokenizer = AutoTokenizer.from_pretrained(settings.base_model, token=settings.hf_token or None)
    model = AutoModelForCausalLM.from_pretrained(settings.base_model, token=settings.hf_token or None)
    return pipeline("text-generation", model=model, tokenizer=tokenizer)


def _run_generation(prompt: str) -> dict:
    generator = get_generator()

    start = time.perf_counter()
    output = generator(
        prompt,
        max_new_tokens=settings.max_new_tokens,
        do_sample=False,
        num_return_sequences=1,
        pad_token_id=generator.tokenizer.eos_token_id,
    )
    latency_ms = int((time.perf_counter() - start) * 1000)

    full_text = output[0]["generated_text"]
    answer = full_text[len(prompt):].strip()

    input_tokens = len(generator.tokenizer.encode(prompt))
    output_tokens = len(generator.tokenizer.encode(answer))

    return {
        "answer": answer,
        "latency_ms": latency_ms,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        # Local open-weight inference: no per-token API cost.
        "cost_usd": 0.0,
    }


def generate_rag_answer(question: str, context: str) -> dict:
    prompt = RAG_PROMPT_TEMPLATE.format(context=context, question=question)
    return _run_generation(prompt)


def generate_base_answer(question: str) -> dict:
    """No retrieval, no fine-tuning — the plain base model answering cold.
    This is the third leg of the head-to-head comparison."""
    prompt = BASE_PROMPT_TEMPLATE.format(question=question)
    return _run_generation(prompt)