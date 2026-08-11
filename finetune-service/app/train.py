import os

from datasets import Dataset
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
from trl import SFTTrainer

from app.config import get_settings
from app.data_gen import fetch_all_qa_pairs

settings = get_settings()

PROMPT_TEMPLATE = """### Question:
{question}

### Answer:
{answer}"""


def build_dataset() -> Dataset:
    pairs = fetch_all_qa_pairs()
    if not pairs:
        raise RuntimeError("No synthetic Q&A pairs found — run /generate-data before /train")

    texts = [PROMPT_TEMPLATE.format(question=p["question"], answer=p["answer"]) for p in pairs]
    return Dataset.from_dict({"text": texts})


def run_finetune_job() -> dict:
    """Runs a LoRA fine-tune on the base model using synthetic Q&A pairs.
    Intended to run as an RQ background job — this is a long-running, blocking call."""
    dataset = build_dataset()

    tokenizer = AutoTokenizer.from_pretrained(settings.finetune_base_model, token=settings.hf_token or None)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(settings.finetune_base_model, token=settings.hf_token or None)

    lora_config = LoraConfig(
        r=settings.lora_r,
        lora_alpha=settings.lora_alpha,
        lora_dropout=settings.lora_dropout,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    )
    model = get_peft_model(model, lora_config)

    os.makedirs(settings.lora_output_dir, exist_ok=True)

    training_args = TrainingArguments(
        output_dir=settings.lora_output_dir,
        num_train_epochs=settings.num_train_epochs,
        per_device_train_batch_size=settings.per_device_batch_size,
        learning_rate=settings.learning_rate,
        logging_steps=10,
        save_strategy="epoch",
        report_to=[],
    )

    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        tokenizer=tokenizer,
        dataset_text_field="text",
        max_seq_length=512,
    )

    trainer.train()
    trainer.save_model(settings.lora_output_dir)
    tokenizer.save_pretrained(settings.lora_output_dir)

    return {
        "status": "complete",
        "adapter_path": settings.lora_output_dir,
        "training_examples": len(dataset),
    }