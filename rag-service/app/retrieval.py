from app.config import get_settings
from app.db import search_similar_chunks
from app.embeddings import embed_text

settings = get_settings()


def retrieve_context(question: str, top_k: int | None = None) -> list[dict]:
    query_vector = embed_text(question)
    k = top_k or settings.top_k
    return search_similar_chunks(query_vector, top_k=k)


def build_context_block(chunks: list[dict]) -> str:
    if not chunks:
        return "No relevant context was found in the corpus."
    parts = []
    for i, c in enumerate(chunks, start=1):
        parts.append(f"[{i}] (source: {c['filename']})\n{c['content']}")
    return "\n\n".join(parts)