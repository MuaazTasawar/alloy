from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgres://alloy:alloy_dev_password@postgres:5432/alloy?sslmode=disable"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    base_model: str = "microsoft/Phi-3-mini-4k-instruct"
    hf_token: str = ""

    chunk_size_tokens: int = 300
    chunk_overlap_tokens: int = 50
    top_k: int = 4
    max_new_tokens: int = 256

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()