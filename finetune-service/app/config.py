from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgres://alloy:alloy_dev_password@postgres:5432/alloy?sslmode=disable"
    redis_url: str = "redis://redis:6379/0"

    finetune_base_model: str = "meta-llama/Llama-3.2-3B-Instruct"
    hf_token: str = ""
    lora_output_dir: str = "/app/adapters/latest"

    # LoRA hyperparameters
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    learning_rate: float = 2e-4
    num_train_epochs: int = 3
    per_device_batch_size: int = 2

    # Synthetic data generation
    anthropic_api_key: str = ""
    synthetic_pairs_per_document: int = 15

    max_new_tokens: int = 256

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()