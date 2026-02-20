# Architecture Diagrams

Three Mermaid diagrams: **project architecture** (clean layers + data flow), **Docker setup** (how containers connect), and **deployment** (AWS).

---

## 1. Project Architecture

High-level: entry points (FastAPI + Streamlit) → copilot orchestration → infrastructure (DB, memory, RAG, tools) and external LLM.

```mermaid
flowchart TB
    subgraph Presentation["Presentation Layer"]
        FastAPI["main.py\n(FastAPI routes)"]
        Streamlit["app.py\n(Streamlit dashboard)"]
    end

    subgraph Application["Application Layer"]
        Copilot["copilot.py\n(Orchestrator: Mem0 + RAG + tools → draft)"]
    end

    subgraph Domain["Domain"]
        Models["models.py\n(Pydantic schemas)"]
    end

    subgraph Infrastructure["Infrastructure Layer"]
        Database["database.py\n(SQLite)"]
        Memory["memory.py\n(Mem0 + ChromaDB)"]
        RAG["rag.py\n(Docs → ChromaDB)"]
        Tools["tools.py\n(Mock CRM + billing)"]
        Config["config.py\n(Settings)"]
    end

    subgraph Data["Data Stores"]
        SQLite[("support.db\n(customers, tickets, drafts)")]
        ChromaRAG[("chroma_rag/\n(KB vectors)")]
        ChromaMem0[("chroma_mem0/\n(Customer memories)")]
    end

    subgraph External["External"]
        LLM["ChatGroq (LLM)"]
    end

    FastAPI --> Copilot
    Streamlit --> Copilot
    FastAPI --> Database
    Streamlit --> Database
    Copilot --> Models
    Copilot --> Memory
    Copilot --> RAG
    Copilot --> Tools
    Copilot --> LLM
    Memory --> ChromaMem0
    RAG --> ChromaRAG
    Database --> SQLite
    Tools --> Database
    Config -.-> Copilot
    Config -.-> RAG
    Config -.-> Memory
```

**Flow (ticket → draft):** Ticket (webhook/form) → `main.py` → save to SQLite + BackgroundTasks → `copilot.py` → customer lookup (SQLite) + Mem0 search + RAG search + optional tool calls → LLM draft → save draft to SQLite → dashboard shows ticket + draft.

---

## 2. Docker Architecture (local development)

Two containers share one image and one named volume. The `dashboard` talks to the `api` over Docker's internal network.

```mermaid
flowchart TB
    Dev["Developer\n(localhost)"]

    subgraph DockerCompose["docker-compose.yml"]
        subgraph ApiContainer["Container: api\n(python main.py)"]
            FastAPI["FastAPI\nport 8000"]
        end

        subgraph DashContainer["Container: dashboard\n(streamlit run app.py)"]
            Streamlit["Streamlit\nport 8501"]
        end

        Volume[("Named volume: data/\nsupport.db\nchroma_rag/\nchroma_mem0/")]
    end

    subgraph External["External"]
        LLM["ChatGroq (LLM)\nvia GROQ_API_KEY"]
    end

    Dev -->|"localhost:8000"| FastAPI
    Dev -->|"localhost:8501"| Streamlit
    Streamlit -->|"http://api:8000\n(internal network)"| FastAPI
    FastAPI --- Volume
    DashContainer --- Volume
    FastAPI -->|HTTPS| LLM
```

**Key points for beginners:**
- Both containers are built from the **same `Dockerfile`** — they're identical images, just started with different commands
- The `data/` volume is like a shared USB drive — both containers read/write the same SQLite + ChromaDB files
- `http://api:8000` is Docker's internal hostname — containers talk to each other by service name, not `localhost`
- `.env` file is passed to both containers so they get the `GROQ_API_KEY`

**Files added:**
```
Dockerfile            # FROM python:3.11-slim → COPY code → pip install
docker-compose.yml    # defines api + dashboard services + data volume
```

---

## 3. Deployment Architecture (AWS)

Single EC2 instance runs both Docker containers; optional nginx + SSL in front. S3 for KB/backups; Elastic IP for a fixed address.

```mermaid
flowchart TB
    User["User / Support Agent"]
    DNS["Elastic IP\n(static)"]

    subgraph AWS["AWS"]
        subgraph EC2["EC2 (t2.micro, Ubuntu 22.04)"]
            subgraph Optional["Optional"]
                Nginx["nginx\n(reverse proxy + Let's Encrypt SSL)"]
            end
            subgraph DockerCompose["docker compose up"]
                API["api container\nFastAPI port 8000"]
                Dashboard["dashboard container\nStreamlit port 8501"]
            end
            subgraph AppData["Named volume (data/)"]
                LocalDB[("support.db")]
                Chroma[("chroma_rag/\nchroma_mem0/")]
            end
        end

        S3["S3\n(KB docs, backups)"]
    end

    User --> DNS
    DNS --> Nginx
    Nginx --> API
    Nginx --> Dashboard
    DNS --> API
    DNS --> Dashboard
    API --> LocalDB
    API --> Chroma
    Dashboard --> API
    EC2 -.->|optional sync| S3
```

**Steps:** Launch EC2 (Ubuntu 22.04, t2.micro) → open ports 8000 + 8501 → SSH in → install Docker + Docker Compose → clone repo → `cp .env.example .env` (add key) → `docker compose up -d` → (optional) nginx + Let's Encrypt. **Cost:** ~$0 on free tier, ~$8–10/mo after.
