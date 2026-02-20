# Customer Support Agent Copilot

AI copilot for support teams built with FastAPI, LangChain, Mem0, ChromaDB, SQLite, and Streamlit.

Drafts include a structured `context_used` payload (signals, highlights, tool calls, memory hits, and knowledge hits), and the dashboard renders this as a context panel for fast review.

## Implementation Reference

For a current code-level handoff and cross-agent reference, see:

- `docs/current-implementation-reference.md`
- `docs/company-cross-contact-memory-test-case.md` (entity-memory demo across two contacts in same company)
- `docs/deployment-ec2-github-actions.md` (simple EC2 CI/CD with GitHub Actions)

## Tech Stack

- Python 3.11
- FastAPI + Uvicorn
- LangChain + ChatGroq
- Mem0 + ChromaDB
- SQLite
- Streamlit
- Docker + docker-compose
- uv (package management)

## Backend Structure

Primary backend code now lives in the package:

- `customer_support_agent/core` (settings)
- `customer_support_agent/schemas` (API schemas)
- `customer_support_agent/repositories/sqlite` (data access)
- `customer_support_agent/integrations` (RAG, memory, tools)
- `customer_support_agent/services` (copilot + workflows)
- `customer_support_agent/api` (dependencies, routers, app factory)

Root files like `main.py`, `config.py`, `database.py`, etc. are compatibility wrappers to keep existing commands/imports stable.

## Prerequisites

- [uv](https://docs.astral.sh/uv/)
- Python 3.11 (uv can install/manage it)

## Setup

```bash
cp .env.example .env
# add GROQ_API_KEY in .env
uv python install 3.11
uv sync --dev
```

## Run Locally

API:
```bash
uv run python main.py
```

Dashboard:
```bash
uv run streamlit run app.py
```

Seed data:
```bash
uv run python seed_data.py
```

## Run with Docker

```bash
docker compose up --build
```

## Run Tests

```bash
uv run pytest -q
```

## Core API Endpoints

- `POST /api/tickets`
- `GET /api/tickets`
- `GET /api/tickets/{id}`
- `POST /api/tickets/{id}/generate-draft`
- `GET /api/drafts/{ticket_id}`
- `PATCH /api/drafts/{id}`
- `POST /api/knowledge/ingest`
- `GET /api/customers/{id}/memories`
