# AI Copilot for Support Agents — Simplified Plan

## Context

Build an AI copilot that helps support agents by surfacing customer context, searching a knowledge base, calling CRM/billing tools, and generating draft responses. This is a **beginner-friendly portfolio project** — the architecture prioritizes clarity and simplicity over production scale.

**What we removed vs the original plan**: No Celery/Redis, no PostgreSQL/pgvector, no Docker Compose, no multi-tenancy, no JWT auth, no WebSockets, no Alembic migrations. Same AI value, 1/3 the files.

**Reference code**: Existing Mem0 + LangChain chatbot at `/Users/yashpatil/Developer/AI/LangChain/mem0/chatbot.py` — we reuse its Mem0 init pattern (lines 58-99), memory search (lines 144-162), and save (lines 164-181).

---

## Stack

```
Python 3.11 + FastAPI + LangChain + ChatGroq + Mem0 + ChromaDB + SQLite + Streamlit + Docker
```

Runs locally with a single `docker compose up` command. No manual pip installs or environment setup.

---

## Project Structure (~14 files)

```
Customer_support_agent/
├── main.py                # FastAPI app — all API routes in one file
├── copilot.py             # ★ The AI brain: Mem0 + RAG + tools → draft
├── memory.py              # Mem0 wrapper (adapted from existing chatbot.py)
├── rag.py                 # Document loading, chunking, ChromaDB retrieval
├── tools.py               # LangChain @tool functions (mock CRM + billing)
├── database.py            # SQLite setup + helper functions
├── models.py              # Pydantic schemas for API request/response
├── config.py              # Settings from .env
├── seed_data.py           # Populate sample customers, tickets, KB docs
├── app.py                 # Streamlit frontend (agent dashboard)
├── pyproject.toml         # Python dependencies (managed by uv)
├── uv.lock                # Locked dependency graph (for reproducible installs)
├── .env.example           # Template for API keys
│
├── docker-compose.yml     # ★ One command to run everything: api + dashboard
├── Dockerfile             # Single Dockerfile — both services use the same image
│
├── knowledge_base/        # Sample docs to ingest into RAG
│   ├── getting-started.md
│   ├── billing-faq.md
│   └── api-troubleshooting.md
│
└── data/                  # Mounted as a Docker volume, gitignored
    ├── support.db         # SQLite database
    ├── chroma_rag/        # ChromaDB for knowledge base vectors
    └── chroma_mem0/       # ChromaDB for Mem0 customer memories
```

### Docker at a Glance (beginner explanation)

> Think of Docker as packaging your app into a "box" that works the same everywhere — no "it works on my machine" problems.

- **`Dockerfile`** — the recipe to build the box: start from Python 3.11, copy code, `uv sync`
- **`docker-compose.yml`** — describes two boxes (services) and how they connect:
  - `api` → runs `uv run python main.py` on port 8000
  - `dashboard` → runs `uv run streamlit run app.py` on port 8501
  - Both share a `data/` volume so SQLite + ChromaDB files persist across restarts

**No new Python concepts needed.** The AI code is identical — Docker just handles the "running" part.

---

## Core Flow

```
1. Ticket arrives (webhook POST or Streamlit form)
       ↓
2. main.py saves ticket to SQLite, triggers BackgroundTasks
       ↓
3. copilot.py orchestrates (all in-process, no Celery):
   a. Look up customer in SQLite
   b. Search Mem0 for customer history  →  "contacted 4x about latency"
   c. Search knowledge base via RAG     →  relevant KB articles
   d. LLM calls tools if needed         →  CRM plan info, billing status
   e. LLM generates draft response with all context
       ↓
4. Draft saved to SQLite
       ↓
5. Streamlit dashboard shows ticket + context + draft
   Agent edits → accepts → Mem0 saves resolution for next time
```

---

## Database (SQLite — 3 tables)

```sql
CREATE TABLE customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    company TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER REFERENCES customers(id),
    subject TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT DEFAULT 'open',
    priority TEXT DEFAULT 'medium',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER REFERENCES tickets(id),
    content TEXT NOT NULL,
    context_used TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## The 5 Key Files (read in this order)

1. **`config.py`** — Where settings come from
2. **`copilot.py`** — The AI brain (most important file)
3. **`rag.py`** — How documents become searchable
4. **`tools.py`** — How the LLM looks things up
5. **`main.py`** — How HTTP connects to AI

---

## API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /api/tickets` | Create a ticket (or receive webhook) |
| `GET /api/tickets` | List all tickets |
| `GET /api/tickets/{id}` | Ticket detail + customer info |
| `POST /api/tickets/{id}/generate-draft` | Trigger AI draft generation |
| `GET /api/drafts/{ticket_id}` | Get draft for a ticket |
| `PATCH /api/drafts/{id}` | Accept/discard a draft |
| `POST /api/knowledge/ingest` | Ingest KB documents into RAG |
| `GET /api/customers/{id}/memories` | View Mem0 memories for a customer |

---

## Build Order

### Phase 1 — Core AI Pipeline
1. `config.py` + `.env.example` + `pyproject.toml`
2. `database.py` — SQLite setup with 3 tables
3. `memory.py` — Mem0 wrapper with ChromaDB backend
4. `rag.py` — document ingestion + retrieval
5. `tools.py` — mock CRM and billing tools
6. `copilot.py` — wire Mem0 + RAG + tools + LLM → draft
7. `seed_data.py` — sample customers, tickets, KB docs
8. `main.py` — FastAPI routes
9. `models.py` — Pydantic schemas

**Milestone**: `python main.py` → POST a ticket at `/docs` → AI draft appears with customer memory + KB context + tool results

### Phase 2 — Dashboard + Polish
10. `app.py` — Streamlit dashboard
11. "Accept draft" flow: updates ticket status + saves resolution to Mem0
12. KB upload via Streamlit file uploader
13. `README.md` with setup guide

**Milestone**: `streamlit run app.py` → full end-to-end flow visible in UI

### Phase 3 — Docker
14. `Dockerfile` — single image for both services
15. `docker-compose.yml` — `api` + `dashboard` services with shared `data/` volume
16. Update `README.md` with Docker instructions

**Milestone**: `docker compose up` → both services running, end-to-end flow works inside containers

---

## How to Run

### Option A — Docker (recommended)
```bash
cp .env.example .env              # add your GROQ_API_KEY
docker compose up --build         # builds image + starts api & dashboard
# In a separate terminal, seed sample data:
docker compose exec api uv run python seed_data.py
```
- FastAPI → http://localhost:8000/docs
- Streamlit → http://localhost:8501

### Option B — Plain Python (no Docker)
```bash
uv sync
cp .env.example .env              # add your GROQ_API_KEY
uv run python seed_data.py        # populate sample data
uv run python main.py             # FastAPI on http://localhost:8000
uv run streamlit run app.py       # Streamlit on http://localhost:8501 (new terminal)
```

No database servers. No Redis. Just Python (or Docker).

---

## Deployment (AWS)

| AWS Service | Purpose | Free Tier |
|-------------|---------|-----------|
| **EC2** (t2.micro) | Run FastAPI + Streamlit | 750 hrs/mo for 12 months |
| **S3** | Store KB docs + backups | 5GB free |
| **Elastic IP** | Static public IP | Free while attached to running instance |

**Steps**:
1. Launch EC2 (Ubuntu 22.04, t2.micro), open ports 8000 + 8501
2. SSH in, install Python 3.11 + uv, clone repo, `uv sync`
3. Run API + Streamlit with `systemd` services
4. (Optional) nginx reverse proxy + Let's Encrypt SSL

**Cost**: ~$0 on free tier, ~$8-10/mo after.

**Scaling later**: ECS Fargate + RDS PostgreSQL + SQS.

---

## Verification

1. **Swagger UI**: POST a ticket at `/docs`, trigger draft, verify context
2. **Streamlit E2E**: Create ticket → see draft → accept → new ticket for same customer → verify Mem0 remembers
3. **RAG check**: Ingest docs → ticket matching KB topic → verify draft references articles
