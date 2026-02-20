"""API flow tests using a mocked copilot."""

from __future__ import annotations

import importlib
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient
import config as config_module
import customer_support_agent.core.settings as package_settings_module

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class FakeRag:
    """Minimal RAG stub for API tests."""

    def ingest_directory(self, directory: Path, clear_existing: bool = False) -> dict[str, int]:
        assert directory.exists()
        return {
            "files_indexed": 3,
            "chunks_indexed": 9,
            "collection_count": 9,
        }


class FakeCopilot:
    """SupportCopilot test double for deterministic API behavior."""

    def __init__(self):
        self.rag = FakeRag()
        self.resolutions: list[dict[str, str]] = []

    def generate_draft(self, ticket: dict, customer: dict) -> dict:
        return {
            "draft": (
                f"Hi {customer['email']}, we reviewed '{ticket['subject']}' and "
                "are actively working on a fix."
            ),
            "context_used": {
                "version": 2,
                "ticket": {
                    "id": ticket.get("id"),
                    "subject": ticket.get("subject"),
                    "priority": ticket.get("priority"),
                    "status": ticket.get("status"),
                },
                "customer": {
                    "id": customer.get("id"),
                    "email": customer.get("email"),
                    "name": customer.get("name"),
                    "company": customer.get("company"),
                },
                "signals": {
                    "memory_hit_count": 1,
                    "knowledge_hit_count": 1,
                    "tool_call_count": 1,
                    "tool_error_count": 0,
                    "knowledge_sources": ["api-troubleshooting.md"],
                },
                "highlights": {
                    "memory": ["prior latency ticket"],
                    "knowledge": ["[api-troubleshooting.md] retry with backoff"],
                    "tools": ["alex@example.com is on the pro plan with 8h SLA."],
                },
                "memory_hits": [{"memory": "prior latency ticket", "score": 0.2}],
                "knowledge_hits": [{"source": "api-troubleshooting.md", "content": "retry with backoff"}],
                "tool_calls": [
                    {
                        "tool_name": "lookup_customer_plan",
                        "tool_call_id": "tool_1",
                        "arguments": {"customer_email": customer["email"]},
                        "status": "ok",
                        "summary": "alex@example.com is on the pro plan with 8h SLA.",
                        "output": {"details": {"plan_tier": "pro", "sla_hours": 8}},
                        "output_text": "{\"summary\":\"alex@example.com is on the pro plan with 8h SLA.\"}",
                    }
                ],
            },
        }

    def list_customer_memories(
        self,
        customer_email: str,
        customer_company: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        _ = (customer_company, limit)
        return [{"memory": f"known-{customer_email}", "score": 0.1, "metadata": {}}]

    def search_customer_memories(
        self,
        customer_email: str,
        query: str,
        customer_company: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        _ = (query, customer_company, limit)
        return [{"memory": f"known-{customer_email}", "score": 0.1, "metadata": {}}]

    def save_accepted_resolution(
        self,
        customer_email: str,
        customer_company: str | None,
        ticket_subject: str,
        ticket_description: str,
        draft_content: str,
        context_used: dict | None = None,
    ) -> None:
        self.resolutions.append(
            {
                "customer_email": customer_email,
                "customer_company": customer_company,
                "ticket_subject": ticket_subject,
                "ticket_description": ticket_description,
                "draft_content": draft_content,
                "context_used": context_used or {},
            }
        )


class FailingCopilotFactory:
    """Callable that simulates unavailable copilot dependencies."""

    def __call__(self):
        raise RuntimeError("GROQ_API_KEY is missing")


@pytest.fixture()
def env_setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    data_dir = tmp_path / "data"
    kb_dir = tmp_path / "knowledge_base"
    kb_dir.mkdir(parents=True, exist_ok=True)
    (kb_dir / "sample.md").write_text("sample kb", encoding="utf-8")

    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setenv("DB_PATH", str(data_dir / "support.db"))
    monkeypatch.setenv("CHROMA_RAG_DIR", str(data_dir / "chroma_rag"))
    monkeypatch.setenv("CHROMA_MEM0_DIR", str(data_dir / "chroma_mem0"))
    monkeypatch.setenv("KNOWLEDGE_BASE_DIR", str(kb_dir))


@pytest.fixture()
def client_with_fake_copilot(env_setup, monkeypatch: pytest.MonkeyPatch):
    config_module.get_settings.cache_clear()
    package_settings_module.get_settings.cache_clear()

    import main as main_module
    import customer_support_agent.api.dependencies as deps_module
    import customer_support_agent.api.routers.tickets as tickets_router_module
    import customer_support_agent.api.routers.drafts as drafts_router_module

    main_module = importlib.reload(main_module)
    fake = FakeCopilot()
    monkeypatch.setattr(deps_module, "get_copilot", lambda: fake)
    monkeypatch.setattr(tickets_router_module, "get_copilot", lambda: fake)
    monkeypatch.setattr(drafts_router_module, "get_copilot", lambda: fake)

    with TestClient(main_module.app) as client:
        yield client, fake


@pytest.fixture()
def client_with_failing_copilot(env_setup, monkeypatch: pytest.MonkeyPatch):
    config_module.get_settings.cache_clear()
    package_settings_module.get_settings.cache_clear()

    import main as main_module
    import customer_support_agent.api.dependencies as deps_module
    import customer_support_agent.api.routers.tickets as tickets_router_module

    main_module = importlib.reload(main_module)
    failing = FailingCopilotFactory()
    monkeypatch.setattr(deps_module, "get_copilot", failing)
    monkeypatch.setattr(tickets_router_module, "get_copilot", failing)

    with TestClient(main_module.app) as client:
        yield client


def test_ticket_to_draft_accept_flow(client_with_fake_copilot):
    client, fake = client_with_fake_copilot

    create_payload = {
        "customer_email": "alex@example.com",
        "customer_name": "Alex",
        "customer_company": "Acme",
        "subject": "API latency in EU region",
        "description": "Our users report API latency spikes and intermittent timeout errors.",
        "priority": "high",
        "auto_generate": False,
    }
    create_response = client.post("/api/tickets", json=create_payload)
    assert create_response.status_code == 200
    ticket = create_response.json()

    generate_response = client.post(f"/api/tickets/{ticket['id']}/generate-draft")
    assert generate_response.status_code == 200
    generated = generate_response.json()["draft"]
    assert generated["status"] == "pending"
    assert "actively working" in generated["content"]
    assert generated["context_used"]["version"] == 2
    assert generated["context_used"]["signals"]["tool_call_count"] == 1
    assert generated["context_used"]["tool_calls"][0]["tool_name"] == "lookup_customer_plan"

    draft_response = client.get(f"/api/drafts/{ticket['id']}")
    assert draft_response.status_code == 200
    draft = draft_response.json()
    assert draft["id"] == generated["id"]

    updated_content = draft["content"] + " We will update you within 2 hours."
    accept_response = client.patch(
        f"/api/drafts/{draft['id']}",
        json={"content": updated_content, "status": "accepted"},
    )
    assert accept_response.status_code == 200
    accepted = accept_response.json()
    assert accepted["status"] == "accepted"

    ticket_response = client.get(f"/api/tickets/{ticket['id']}")
    assert ticket_response.status_code == 200
    assert ticket_response.json()["status"] == "resolved"

    memories_response = client.get(f"/api/customers/{ticket['customer_id']}/memories")
    assert memories_response.status_code == 200
    memories = memories_response.json()["memories"]
    assert len(memories) == 1

    memory_search_response = client.get(
        f"/api/customers/{ticket['customer_id']}/memory-search",
        params={"query": "latency", "limit": 5},
    )
    assert memory_search_response.status_code == 200
    memory_search = memory_search_response.json()
    assert memory_search["query"] == "latency"
    assert len(memory_search["results"]) == 1

    ingest_response = client.post("/api/knowledge/ingest", json={"clear_existing": False})
    assert ingest_response.status_code == 200
    assert ingest_response.json()["files_indexed"] >= 1

    assert len(fake.resolutions) == 1
    assert fake.resolutions[0]["customer_email"] == "alex@example.com"
    assert fake.resolutions[0]["customer_company"] == "Acme"
    assert fake.resolutions[0]["context_used"].get("version") == 2


def test_auto_generate_creates_failed_draft_when_copilot_unavailable(client_with_failing_copilot):
    client = client_with_failing_copilot

    create_payload = {
        "customer_email": "nina@example.com",
        "subject": "Billing portal is unavailable",
        "description": "Clicking invoices returns a server error every time.",
        "priority": "medium",
        "auto_generate": True,
    }
    create_response = client.post("/api/tickets", json=create_payload)
    assert create_response.status_code == 200
    ticket = create_response.json()

    draft_response = client.get(f"/api/drafts/{ticket['id']}")
    assert draft_response.status_code == 200
    draft = draft_response.json()
    assert draft["status"] == "failed"
    assert "Automatic draft generation failed" in draft["content"]
    context = draft.get("context_used") or {}
    assert context.get("version") == 2
    assert context.get("signals", {}).get("tool_error_count") == 1
    assert context.get("errors")

    ingest_response = client.post("/api/knowledge/ingest", json={"clear_existing": False})
    assert ingest_response.status_code == 200
    assert ingest_response.json()["files_indexed"] >= 1
