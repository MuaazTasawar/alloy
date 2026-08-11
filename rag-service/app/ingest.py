from app.config import get_settings
from app.db import insert_chunk, insert_document
from app.embeddings import embed_batch

settings = get_settings()


def chunk_text(text: str, chunk_size_tokens: int, overlap_tokens: int) -> list[str]:
    """Simple whitespace-token chunker with overlap. Good enough for MVP corpora."""
    words = text.split()
    if not words:
        return []

    chunks = []
    step = max(chunk_size_tokens - overlap_tokens, 1)
    for start in range(0, len(words), step):
        window = words[start : start + chunk_size_tokens]
        if not window:
            break
        chunks.append(" ".join(window))
        if start + chunk_size_tokens >= len(words):
            break
    return chunks


def ingest_document(filename: str, raw_text: str, source_type: str = "upload") -> dict:
    document_id = insert_document(filename=filename, source_type=source_type, raw_text=raw_text)

    pieces = chunk_text(raw_text, settings.chunk_size_tokens, settings.chunk_overlap_tokens)
    if not pieces:
        return {"document_id": document_id, "chunks_created": 0}

    embeddings = embed_batch(pieces)

    for idx, (piece, vector) in enumerate(zip(pieces, embeddings)):
        insert_chunk(
            document_id=document_id,
            chunk_index=idx,
            content=piece,
            embedding=vector,
            token_count=len(piece.split()),
        )

    return {"document_id": document_id, "chunks_created": len(pieces)}