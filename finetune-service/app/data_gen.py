import json

import psycopg2
import psycopg2.extras
from anthropic import Anthropic

from app.config import get_settings

settings = get_settings()

SYNTHETIC_QA_PROMPT = """Generate {n} diverse question-and-answer pairs strictly grounded in the
text below. Questions should resemble what a real user would ask about this domain. Answers must
be fully supported by the text — do not invent facts.

Respond ONLY with a JSON array like:
[{{"question": "...", "answer": "..."}}, ...]

Text:
{text}
"""


def _get_conn():
    return psycopg2.connect(settings.database_url)


def fetch_documents() -> list[dict]:
    with _get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT id, filename, raw_text FROM documents ORDER BY created_at ASC")
            return list(cur.fetchall())


def save_qa_pairs(document_id: str, pairs: list[dict]) -> None:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            for pair in pairs:
                cur.execute(
                    """
                    INSERT INTO synthetic_qa_pairs (document_id, question, answer)
                    VALUES (%s, %s, %s)
                    """,
                    (document_id, pair["question"], pair["answer"]),
                )
        conn.commit()


def generate_pairs_for_document(client: Anthropic, doc: dict, n: int) -> list[dict]:
    prompt = SYNTHETIC_QA_PROMPT.format(n=n, text=doc["raw_text"][:8000])

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = "".join(block.text for block in response.content if block.type == "text")
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        pairs = json.loads(raw)
    except json.JSONDecodeError:
        return []

    return [p for p in pairs if "question" in p and "answer" in p]


def generate_synthetic_dataset() -> dict:
    """Walks every ingested document and generates synthetic Q&A pairs via Claude,
    then persists them for the training job to consume."""
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set — required for synthetic data generation")

    client = Anthropic(api_key=settings.anthropic_api_key)
    documents = fetch_documents()

    total_pairs = 0
    for doc in documents:
        pairs = generate_pairs_for_document(client, doc, settings.synthetic_pairs_per_document)
        if pairs:
            save_qa_pairs(doc["id"], pairs)
            total_pairs += len(pairs)

    return {"documents_processed": len(documents), "pairs_generated": total_pairs}


def fetch_all_qa_pairs() -> list[dict]:
    with _get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT question, answer FROM synthetic_qa_pairs ORDER BY created_at ASC")
            return list(cur.fetchall())