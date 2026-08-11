import json
from contextlib import contextmanager

import psycopg2
import psycopg2.extras
from psycopg2.pool import SimpleConnectionPool

from app.config import get_settings

settings = get_settings()

_pool: SimpleConnectionPool | None = None


def init_pool() -> None:
    global _pool
    if _pool is None:
        _pool = SimpleConnectionPool(1, 10, dsn=settings.database_url)


@contextmanager
def get_conn():
    if _pool is None:
        init_pool()
    conn = _pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)


def insert_document(filename: str, source_type: str, raw_text: str) -> str:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO documents (filename, source_type, raw_text)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (filename, source_type, raw_text),
            )
            return str(cur.fetchone()[0])


def insert_chunk(document_id: str, chunk_index: int, content: str, embedding: list[float], token_count: int) -> str:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO chunks (document_id, chunk_index, content, embedding, token_count)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (document_id, chunk_index, content, json.dumps(embedding), token_count),
            )
            return str(cur.fetchone()[0])


def search_similar_chunks(query_embedding: list[float], top_k: int) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT c.id, c.content, c.document_id, d.filename,
                       1 - (c.embedding <=> %s::vector) AS similarity
                FROM chunks c
                JOIN documents d ON d.id = c.document_id
                ORDER BY c.embedding <=> %s::vector
                LIMIT %s
                """,
                (json.dumps(query_embedding), json.dumps(query_embedding), top_k),
            )
            return list(cur.fetchall())


def insert_synthetic_qa_pair(document_id: str, question: str, answer: str) -> str:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO synthetic_qa_pairs (document_id, question, answer)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (document_id, question, answer),
            )
            return str(cur.fetchone()[0])


def fetch_all_synthetic_qa_pairs() -> list[dict]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT question, answer FROM synthetic_qa_pairs ORDER BY created_at ASC")
            return list(cur.fetchall())