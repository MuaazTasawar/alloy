# Alloy

> A self-hosted LLM ops platform that routes each query to RAG, a fine-tuned model, or the base model — and proves which one won.

---

## Table of Contents

1. [Overview](#overview)
2. [The Problem This Solves](#the-problem-this-solves)
3. [How It Works (Architecture)](#how-it-works-architecture)
4. [Tech Stack](#tech-stack)
5. [Features](#features)
6. [Project Structure](#project-structure)
7. [Prerequisites](#prerequisites)
8. [Getting Started](#getting-started)
9. [Environment Variables](#environment-variables)
10. [Running the App](#running-the-app)
11. [Using Alloy: A Walkthrough](#using-alloy-a-walkthrough)
12. [API Reference](#api-reference)
13. [Database Schema](#database-schema)
14. [Phase Build History](#phase-build-history)
15. [Troubleshooting](#troubleshooting)
16. [Roadmap / What Was Cut for MVP](#roadmap--what-was-cut-for-mvp)
17. [Contributing](#contributing)
18. [License](#license)

---

## Overview

Alloy is a self-hosted platform that answers one question with **three different AI strategies at once** — a raw base model, a Retrieval-Augmented Generation (RAG) pipeline, and a LoRA-fine-tuned model — and then uses an LLM-as-judge to score all three and declare a winner, showing latency and cost side by side.

It exists to answer a question every small AI team eventually faces: *"Should we use RAG, fine-tuning, or just the base model for this?"* Instead of guessing, testing manually, or stitching together disconnected tools, Alloy gives you one dashboard where you upload your domain data once, and it automatically builds a RAG index **and** fine-tunes a small model on that same data — then lets you watch them compete on real questions, in real time.

Once you've run enough comparisons, you can flip on **Auto-Route mode**, and Alloy will silently send every future question straight to whichever strategy has been winning — no more manual judging required.

---

## The Problem This Solves

Small AI teams and solo builders end up stitching together separate, disconnected tools:

- Retrieval → LangChain + a vector DB, configured by hand
- Fine-tuning → a one-off Colab notebook, run once and forgotten
- Evaluation → manual spot-checking, if it happens at all

Enterprise tools like LangSmith or Weights & Biases exist, but they're heavy, hosted, and priced for teams — not for someone trying to figure out, *before they build anything real*, whether their use case even needs fine-tuning or whether RAG alone would do the job just as well for a fraction of the engineering cost.

Alloy answers that question directly, with real numbers, on your own data, self-hosted.

---

## How It Works (Architecture)

```
                              ┌─────────────────────┐
                              │   Next.js Dashboard  │
                              │  (comparison UI,     │
                              │   auto-route toggle) │
                              └──────────┬───────────┘
                                         │ HTTP
                                         ▼
                              ┌─────────────────────┐
                              │   Go Gateway (Fiber)  │
                              │  routing + fan-out    │
                              │  + persistence layer  │
                              └──────────┬───────────┘
                     ┌───────────────────┼───────────────────┐
                     │                   │                   │
                     ▼                   ▼                   ▼
          ┌───────────────────┐ ┌───────────────────┐ ┌──────────────────┐
          │   RAG Service       │ │ Fine-Tune Service  │ │  Judge Service    │
          │  (FastAPI)          │ │  (FastAPI)          │ │  (FastAPI)         │
          │  - ingestion         │ │  - synthetic data   │ │  - LLM-as-judge    │
          │  - embeddings         │ │    generation        │ │    scoring          │
          │  - pgvector search    │ │  - LoRA fine-tune     │ │  - head-to-head      │
          │  - base model +       │ │    (background job)   │ │    comparison        │
          │    RAG generation     │ │  - fine-tuned inference│ │    verdict           │
          └──────────┬────────────┘ └──────────┬────────────┘ └──────────┬─────────┘
                     │                          │                          │
                     ▼                          ▼                          │
          ┌────────────────────────────────────────────┐                  │
          │      Postgres + pgvector (shared)             │◄─────────────┘
          │  documents, chunks, synthetic Q&A pairs,       │
          │  queries, responses, judge_scores,             │
          │  routing_state                                  │
          └────────────────────────────────────────────┘
                                         ▲
                                         │
                              ┌─────────────────────┐
                              │        Redis           │
                              │  job queue for LoRA     │
                              │  fine-tune training       │
                              └─────────────────────┘
```

**The core flow, step by step:**

1. **Ingest** — You upload a text document to the RAG service. It's chunked, embedded (using `sentence-transformers`), and stored in Postgres with the `pgvector` extension.
2. **Generate synthetic training data** — The fine-tune service calls Claude to generate realistic question/answer pairs grounded strictly in your uploaded documents, since real domain Q&A data rarely exists upfront.
3. **Fine-tune** — Those synthetic pairs train a LoRA adapter on top of a small open-weight base model (e.g. Llama 3.2 3B), as a background job tracked through Redis/RQ so the API responds immediately with a job ID instead of blocking.
4. **Ask a question** — You type one question into the dashboard. The Go gateway fans it out concurrently to all three strategies:
   - **Base model** — the untouched open-weight model, no context, no fine-tuning.
   - **RAG** — the same base model, but with the most relevant chunks from your corpus injected into the prompt.
   - **Fine-tuned** — the LoRA-adapted model, answering from what it learned during training.
5. **Judge** — All three answers go to the judge service in a single call to Claude, which scores each on correctness, relevance, and clarity, and picks a winner with reasoning.
6. **Compare** — The dashboard renders all three answers side by side with latency, token counts, cost, and the judge's score — this is the "wow moment": one question, three answers, one verdict.
7. **Auto-route** — Flip the toggle, and the gateway stops fanning out entirely. It routes every subsequent question straight to the last winning strategy, skipping the judge call for speed.

---

## Tech Stack

| Layer                  | Technology                                              | Why                                                                 |
|-------------------------|-----------------------------------------------------------|----------------------------------------------------------------------|
| Routing / Orchestration | Go (Fiber)                                                | Fast, concurrent fan-out to 3 backends; a genuine differentiator from the typical all-Python AI infra project |
| RAG + Fine-Tune Backend | Python (FastAPI)                                          | Industry-standard for ML tooling — HuggingFace `transformers`, `peft`, `sentence-transformers` |
| Fine-Tuning Method       | LoRA / QLoRA via HuggingFace `peft`                       | Cheap, fast, parameter-efficient fine-tuning suited to small open-weight models |
| Vector Database          | PostgreSQL + `pgvector`                                   | One database for both structured app data and embeddings — no separate vector DB to run |
| Job Queue                | Redis + RQ                                                | Fine-tune jobs run for minutes to hours; queued as background jobs instead of blocking an HTTP request |
| Frontend                 | Next.js 14 (App Router) + TypeScript + Tailwind CSS + Recharts | Server-friendly React framework with fast iteration and built-in charting |
| Evaluation                | Anthropic Claude API (`claude-sonnet-4-6`) as LLM-judge     | Used only to *evaluate* answers and generate synthetic training data — never as the thing being evaluated |
| Base / Fine-Tuned Models  | Small open-weight models (e.g. Llama 3.2 3B, Phi-3-mini) | Runs locally / on a free-tier GPU (Colab/Kaggle for training) — no per-token inference cost |
| Containerization           | Docker + Docker Compose                                    | One command spins up all 6 services plus Postgres and Redis          |

---

## Features

- **Three-way live comparison** — one question, three simultaneous answers (base model, RAG, fine-tuned), each with its own latency, token count, and cost.
- **Automated LLM-as-judge scoring** — every comparison is scored out of 10 with a written explanation of why the winning answer won.
- **Auto-route mode** — a toggle that, once a strategy has proven itself, silently routes all future questions to it, skipping the judge call.
- **Self-serve document ingestion** — upload any UTF-8 text document; it's automatically chunked, embedded, and indexed for RAG.
- **Synthetic training data generation** — no need to hand-write Q&A pairs; Claude generates them from your own corpus, grounded strictly in the source text.
- **Background LoRA fine-tuning** — training runs as a queued job with pollable status, so it never blocks the API.
- **Cost & latency observability** — every response is logged to Postgres with token counts and cost, visualized as a bar chart in the dashboard.
- **Health & readiness checks on every service** — each backend exposes `/health` (and `/ready` where relevant) for container orchestration.
- **Graceful shutdown** — the Go gateway drains in-flight requests on SIGTERM/SIGINT instead of dropping them.
- **Retry logic on the judge service** — transient Anthropic API errors are retried with backoff instead of failing the whole comparison.

---

## Project Structure

```
alloy/
├── gateway/                        # Go routing + orchestration layer
│   ├── cmd/
│   │   └── gateway/
│   │       └── main.go             # Entry point, graceful shutdown
│   ├── internal/
│   │   ├── config/
│   │   │   └── config.go           # Env-based configuration loader
│   │   ├── db/
│   │   │   └── db.go               # Postgres pool + query helpers
│   │   ├── models/
│   │   │   └── response.go         # Shared request/response DTOs
│   │   ├── clients/
│   │   │   ├── rag_client.go       # HTTP client -> rag-service
│   │   │   ├── finetune_client.go  # HTTP client -> finetune-service
│   │   │   └── judge_client.go     # HTTP client -> judge-service
│   │   ├── router/
│   │   │   └── router.go           # Fiber route table + middleware
│   │   └── handlers/
│   │       ├── query.go            # /query — fan-out + judge + persist
│   │       └── autoroute.go        # /query/auto, /autoroute[/toggle]
│   └── go.mod
├── rag-service/                    # Python FastAPI: RAG pipeline + base model
│   ├── app/
│   │   ├── main.py                 # API routes
│   │   ├── config.py               # Pydantic settings
│   │   ├── db.py                   # Postgres + pgvector queries
│   │   ├── embeddings.py           # sentence-transformers embedding calls
│   │   ├── ingest.py               # Chunking + ingestion pipeline
│   │   ├── retrieval.py            # Vector similarity search
│   │   └── generation.py           # Base model + RAG generation
│   ├── requirements.txt
│   └── Dockerfile
├── finetune-service/                # Python FastAPI: LoRA fine-tuning
│   ├── app/
│   │   ├── main.py                 # API routes + RQ job queueing
│   │   ├── config.py                # Pydantic settings incl. LoRA hyperparams
│   │   ├── data_gen.py              # Synthetic Q&A generation via Claude
│   │   ├── train.py                 # LoRA training job (runs via RQ worker)
│   │   └── inference.py             # Fine-tuned model inference
│   ├── requirements.txt
│   └── Dockerfile
├── judge-service/                   # Python FastAPI: LLM-as-judge
│   ├── app/
│   │   ├── main.py                  # API routes
│   │   ├── config.py                 # Pydantic settings
│   │   └── judge.py                  # Scoring prompts + retry logic
│   ├── requirements.txt
│   └── Dockerfile
├── dashboard/                        # Next.js comparison UI
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx              # Main dashboard page
│   │   │   ├── layout.tsx            # Root layout
│   │   │   └── globals.css           # Tailwind entrypoint
│   │   ├── components/
│   │   │   ├── QueryInput.tsx        # Question input + submit
│   │   │   ├── ResponseCard.tsx      # Single strategy's answer card
│   │   │   ├── ComparisonView.tsx    # Side-by-side 3-card layout
│   │   │   ├── AutoRouteToggle.tsx   # Auto-route on/off switch
│   │   │   └── CostLatencyChart.tsx  # Recharts bar chart
│   │   ├── lib/
│   │   │   └── api.ts                # Gateway API client (with timeouts)
│   │   └── types/
│   │       └── index.ts              # Shared TypeScript types
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── tsconfig.json
├── migrations/                        # Raw SQL, auto-run by Postgres on first boot
│   ├── 001_init.sql                   # Extensions + strategy_type enum
│   ├── 002_documents_chunks.sql       # documents, chunks, synthetic_qa_pairs
│   └── 003_queries_scores.sql         # queries, responses, judge_scores, routing_state
├── docker-compose.yml                 # Orchestrates all 6 services + Postgres + Redis
├── .env.example                       # Template for your local .env
├── .gitignore
└── README.md                          # This file
```

---

## Prerequisites

You'll need the following installed locally:

| Tool             | Minimum Version | Used For                                      |
|-------------------|-------------------|--------------------------------------------------|
| Docker Desktop     | 24.x               | Running Postgres, Redis, and all 6 services       |
| Docker Compose      | v2 (bundled with Docker Desktop) | Orchestrating the multi-service stack        |
| Go                  | 1.22+               | Only needed if developing the gateway outside Docker |
| Python              | 3.11+                | Only needed if developing a Python service outside Docker |
| Node.js             | 18.18+ or 20+         | Only needed if developing the dashboard outside Docker |
| Git                  | any recent version     | Cloning the repo, committing changes                |

You'll also need:

- An **Anthropic API key** (for synthetic data generation and LLM-as-judge scoring) — get one at [console.anthropic.com](https://console.anthropic.com/).
- Optionally, a **HuggingFace access token** if the base or fine-tune model you choose is gated (e.g. some Llama checkpoints require accepting a license on HuggingFace first).
- A GPU is **not required** to run the app end-to-end, but fine-tune training will be very slow on CPU. The MVP scope assumes you'll run the actual `/train` job on a free-tier GPU notebook (Colab or Kaggle) rather than locally, then place the resulting adapter files in `finetune-service`'s adapter volume.

---

## Getting Started

### Clone the Repo

```bash
git clone https://github.com/MuaazTasawar/alloy.git
cd alloy
```

### Installation

**1. Set up your environment file:**

```bash
cp .env.example .env
```

Then open `.env` and fill in the two required secrets:
- `ANTHROPIC_API_KEY` — required for synthetic data generation and judge scoring.
- `HF_TOKEN` — only required if your chosen base/fine-tune model is gated on HuggingFace.

Everything else in `.env.example` has a sensible local default and can be left as-is.

**2. If developing outside Docker**, install dependencies per service:

```bash
# Gateway (Go)
cd gateway
go mod tidy
cd ..

# RAG service (Python)
cd rag-service
pip install -r requirements.txt
cd ..

# Fine-tune service (Python)
cd finetune-service
pip install -r requirements.txt
cd ..

# Judge service (Python)
cd judge-service
pip install -r requirements.txt
cd ..

# Dashboard (Node)
cd dashboard
npm install
cd ..
```

If you're running everything through Docker Compose (recommended), you can skip this step — each service's `Dockerfile` installs its own dependencies inside its container.

---

## Running the App

### Option A — Docker Compose (recommended)

From the repo root, with your `.env` filled in:

```bash
docker compose up --build
```

This will:
1. Start Postgres with the `pgvector` extension and automatically run all three migration files on first boot.
2. Start Redis for the fine-tune job queue.
3. Build and start all four backend services (`rag-service`, `finetune-service`, `judge-service`, `gateway`), waiting for their dependencies' healthchecks to pass first.
4. Build and start the Next.js dashboard.

Once everything is healthy, open:

```
http://localhost:3000
```

To stop everything:

```bash
docker compose down
```

To stop everything **and** wipe the database/adapters (fresh start):

```bash
docker compose down -v
```

### Option B — Running services individually (development mode)

Useful if you're actively editing one service and want fast reload without rebuilding a container.

**Postgres + Redis only, via Docker:**
```bash
docker compose up postgres redis
```

**Gateway:**
```bash
cd gateway
go run ./cmd/gateway
```

**RAG service:**
```bash
cd rag-service
uvicorn app.main:app --reload --port 8001
```

**Fine-tune service:**
```bash
cd finetune-service
uvicorn app.main:app --reload --port 8002
```

**Judge service:**
```bash
cd judge-service
uvicorn app.main:app --reload --port 8003
```

**Dashboard:**
```bash
cd dashboard
npm run dev
```

Make sure the relevant `*_SERVICE_URL` values in your `.env` point to `localhost` and the correct port when running services individually rather than through Docker's internal network.

---

## Using Alloy: A Walkthrough

**1. Ingest a document.**

Upload a plain-text file describing your domain (product docs, course notes, a knowledge base export — anything). Send it to the RAG service:

```bash
curl -X POST http://localhost:8001/ingest \
  -F "file=@your-document.txt"
```

This chunks the document, embeds each chunk, and stores it in `pgvector` for retrieval.

**2. Generate synthetic training data.**

The fine-tune service reads everything you've ingested and asks Claude to generate realistic Q&A pairs grounded in that text:

```bash
curl -X POST http://localhost:8002/generate-data
```

**3. Kick off fine-tuning.**

```bash
curl -X POST http://localhost:8002/train
```

This returns a `job_id` immediately. Training itself runs as a background job — poll its status with:

```bash
curl http://localhost:8002/train/status/<job_id>
```

*(Note: on CPU-only hardware this will be slow. For anything beyond a toy corpus, run this step on a free GPU notebook and place the resulting adapter files into the `finetune-service`'s `/app/adapters/latest` volume before continuing.)*

**4. Ask your first comparison question — in the dashboard.**

Open `http://localhost:3000`, type a question into the input box, and hit **Ask**. Within a few seconds you'll see three cards appear: **Base Model**, **RAG**, and **Fine-Tuned LoRA** — each with its answer, latency, token counts, cost, and a judge score. One card will be highlighted green as the winner, with a short explanation underneath.

**5. Flip on Auto-Route.**

Once at least one comparison has run, the **Auto-Route Mode** toggle becomes available. Turn it on, and every subsequent question you ask goes straight to the winning strategy — no more three-way fan-out, no more judge call, just a fast direct answer.

---

## API Reference

### Gateway (`http://localhost:8080`)

| Method | Path                  | Description                                                            |
|--------|------------------------|---------------------------------------------------------------------------|
| GET    | `/health`               | Liveness check                                                              |
| POST   | `/query`                | Fans a question out to all 3 strategies, judges them, persists everything, returns the full comparison |
| POST   | `/query/auto`            | Routes a question straight to the current winning strategy (requires auto-route to be enabled) |
| GET    | `/autoroute`              | Returns current auto-route state and active strategy                          |
| POST   | `/autoroute/toggle`        | Enables/disables auto-route mode                                               |

**`POST /query` request body:**
```json
{ "question": "What is the refund policy?" }
```

**`POST /query` response body:**
```json
{
  "query_id": "uuid",
  "question": "What is the refund policy?",
  "responses": [
    { "strategy": "base_model", "answer": "...", "latency_ms": 812, "input_tokens": 12, "output_tokens": 96, "cost_usd": 0.0, "score": 4.5, "reasoning": "..." },
    { "strategy": "rag", "answer": "...", "latency_ms": 1043, "input_tokens": 340, "output_tokens": 88, "cost_usd": 0.0, "score": 8.5, "reasoning": "..." },
    { "strategy": "finetuned", "answer": "...", "latency_ms": 690, "input_tokens": 10, "output_tokens": 91, "cost_usd": 0.0, "score": 7.0, "reasoning": "..." }
  ],
  "winner": "rag",
  "winner_reasoning": "RAG cited the specific policy terms directly from the source document, while the other two hallucinated details."
}
```

### RAG Service (`http://localhost:8001`)

| Method | Path         | Description                                          |
|--------|---------------|----------------------------------------------------------|
| GET    | `/health`      | Liveness check                                             |
| GET    | `/ready`       | Readiness check (reports whether DB pool initialized)      |
| POST   | `/ingest`       | Upload + chunk + embed a UTF-8 text document                |
| POST   | `/query`        | RAG-based generation (retrieval + context-grounded answer)   |
| POST   | `/base-query`    | Raw base model generation, no retrieval                       |

### Fine-Tune Service (`http://localhost:8002`)

| Method | Path                       | Description                                              |
|--------|------------------------------|--------------------------------------------------------------|
| GET    | `/health`                     | Liveness + Redis connectivity check                             |
| POST   | `/generate-data`               | Generates synthetic Q&A pairs from all ingested documents         |
| POST   | `/train`                        | Queues a LoRA fine-tune job, returns a job ID                       |
| GET    | `/train/status/{job_id}`         | Polls a training job's status and result                             |
| POST   | `/query`                         | Generates an answer using the fine-tuned model                        |

### Judge Service (`http://localhost:8003`)

| Method | Path        | Description                                                     |
|--------|--------------|-----------------------------------------------------------------|
| GET    | `/health`     | Liveness check                                                     |
| POST   | `/score`       | Scores a single answer                                              |
| POST   | `/compare`      | Scores all three strategies' answers head-to-head and picks a winner  |

---

## Database Schema

All tables live in the shared `alloy` Postgres database and are created automatically from the SQL files in `migrations/` on first container boot.

| Table                | Purpose                                                                          |
|-----------------------|-------------------------------------------------------------------------------------|
| `documents`             | Raw uploaded text documents                                                          |
| `chunks`                 | Chunked + embedded segments of each document, indexed with an IVFFlat vector index    |
| `synthetic_qa_pairs`      | Claude-generated Q&A pairs used to fine-tune the LoRA model                            |
| `queries`                  | Every question asked through the gateway, with its mode (`compare` or `auto_route`) and eventual winning strategy |
| `responses`                 | Each strategy's answer to a query, with latency, token counts, and cost                  |
| `judge_scores`               | The judge's score and reasoning for each individual response                              |
| `routing_state`                | Single-row table tracking whether auto-route is enabled and which strategy is active         |

---

## Phase Build History

| Phase | Name                     | What Was Built                                                                                          |
|-------|---------------------------|------------------------------------------------------------------------------------------------------------|
| 0     | Project Init & Config       | `.gitignore`, `.env.example`, `docker-compose.yml`, all 3 SQL migrations                                     |
| 1     | RAG Service                  | Document ingestion, chunking, embeddings, `pgvector` retrieval, RAG-grounded generation endpoint               |
| 2     | Fine-Tune Service              | Synthetic Q&A generation via Claude, LoRA training pipeline (queued via Redis/RQ), fine-tuned inference endpoint |
| 3     | Judge Service                    | LLM-as-judge scoring — both single-answer scoring and 3-way head-to-head comparison                             |
| 4     | Go Routing Gateway                 | Concurrent fan-out to base model / RAG / fine-tuned, judge integration, result persistence, auto-route logic       |
| 5     | Next.js Comparison Dashboard          | Side-by-side comparison UI, auto-route toggle, cost/latency bar chart, base-query endpoint added to `rag-service` |
| 6     | Polish & Finalize                        | Structured error handling across all services, graceful shutdown, judge-service retry logic, Docker healthchecks, frontend request timeouts |

---

## Troubleshooting

**"could not import ... no required module provides package" (Go, in editor)**
The `go.mod` file only *declares* dependencies — it doesn't download them. Run `go mod tidy` inside `gateway/` to pull down `fiber`, `pgx`, etc. and generate `go.sum`. Restart your editor's Go language server afterward if red squiggles persist.

**"Cannot find module 'react'" / "JSX element implicitly has type 'any'" (Next.js, in editor)**
Same root cause — `package.json` declares dependencies but `npm install` hasn't run yet in `dashboard/`. Run `npm install`, then `npx tsc --noEmit` to confirm a clean type-check.

**RAG or fine-tune service is slow to respond on the first request**
The base/fine-tuned model weights load into memory lazily on first use, not at container startup. The Docker healthchecks give these services a 60-second `start_period` for exactly this reason — the first `/query` after a fresh container start will be noticeably slower than subsequent ones.

**"ANTHROPIC_API_KEY is not set" errors from finetune-service or judge-service**
Make sure `.env` (copied from `.env.example`) has a real key filled in, and that you're passing `--env-file .env` or using `env_file: .env` in Compose (already configured by default).

**Training job stuck in `queued` status forever**
Check that a Redis-backed **RQ worker** is actually running against the `finetune` queue. This MVP scaffold defines the job and the queue, but you'll need to run an RQ worker process (`rq worker finetune --url $REDIS_URL`) alongside the FastAPI service — either as a separate container/process or added to the `finetune-service` Dockerfile's entrypoint, depending on your deployment setup.

**Auto-route toggle stays disabled / greyed out**
Auto-route requires at least one successful `/query` comparison to have run first, so there's a winning strategy to route to. Ask a question through the normal comparison flow before trying to enable it.

---

## Roadmap / What Was Cut for MVP

The following were explicitly out of scope for the 3–4 week MVP build and are natural next steps:

- **Multi-tenant users / auth** — currently single-tenant, no login system.
- **Model swapping UI** — base/fine-tune model choice is currently set via environment variables, not selectable in the dashboard.
- **Training on large corpora** — the demo scope assumes one small-to-medium domain corpus (e.g. a single project's docs), not enterprise-scale document sets.
- **An actual RQ worker container** — the job queue and job definition exist; wiring up a dedicated worker process/container is the next piece to add for `/train` to actually execute end-to-end without manual intervention.
- **Streaming responses** — all three strategies currently return complete answers rather than streaming tokens to the dashboard.
- **Reranking in the RAG pipeline** — retrieval currently uses plain cosine similarity via `pgvector`; a reranking step (e.g. cross-encoder) would improve RAG answer quality further.

---

## Contributing

This is currently a solo portfolio project. If you'd like to suggest a change:

1. Fork the repo.
2. Create a feature branch (`git checkout -b feature/your-feature`).
3. Commit your changes with a clear message.
4. Open a pull request describing what changed and why.

---

## License

MIT