import os
import time
from functools import lru_cache

from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

from app.config import get_settings

settings = get_settings()

INFERENCE_PROMPT = """### Question:
{question}

### Answer:
"""


@lru_cache
def get_finetuned_pipeline():
    tokenizer = AutoTokenizer.from_pretrained(settings.finetune_base_model, token=settings.hf_token or None)
    base_model = AutoModelForCausalLM.from_pretrained(settings.finetune_base_model, token=settings.hf_token or None)

    if os.path.isdir(settings.lora_output_dir) and os.listdir(settings.lora_output_dir):
        model = PeftModel.from_pretrained(base_model, settings.lora_output_dir)
    else:
        # No adapter trained yet — fall back to the untuned base model so the
        # service still responds, rather than hard-failing every request.
        model = base_model

    model.eval()
    return model, tokenizer


def generate_finetuned_answer(question: str) -> dict:
    model, tokenizer = get_finetuned_pipeline()
    prompt = INFERENCE_PROMPT.format(question=question)

    inputs = tokenizer(prompt, return_tensors="pt")

    start = time.perf_counter()
    output_ids = model.generate(
        **inputs,
        max_new_tokens=settings.max_new_tokens,
        do_sample=False,
        pad_token_id=tokenizer.eos_token_id,
    )
    latency_ms = int((time.perf_counter() - start) * 1000)

    generated = tokenizer.decode(output_ids[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)

    return {
        "answer": generated.strip(),
        "latency_ms": latency_ms,
        "input_tokens": inputs["input_ids"].shape[1],
        "output_tokens": output_ids.shape[1] - inputs["input_ids"].shape[1],
        # Local open-weight inference: no per-token API cost.
        "cost_usd": 0.0,
    }