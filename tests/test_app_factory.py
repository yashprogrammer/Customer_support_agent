"""Application factory tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

import customer_support_agent.core.settings as settings_module
from customer_support_agent.api.app_factory import create_app


def test_create_app_registers_expected_routes(tmp_path: Path, monkeypatch):
    data_dir = tmp_path / "data"
    kb_dir = tmp_path / "knowledge_base"
    kb_dir.mkdir(parents=True, exist_ok=True)
    (kb_dir / "sample.md").write_text("sample kb", encoding="utf-8")

    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setenv("DB_PATH", str(data_dir / "support.db"))
    monkeypatch.setenv("CHROMA_RAG_DIR", str(data_dir / "chroma_rag"))
    monkeypatch.setenv("CHROMA_MEM0_DIR", str(data_dir / "chroma_mem0"))
    monkeypatch.setenv("KNOWLEDGE_BASE_DIR", str(kb_dir))
    settings_module.get_settings.cache_clear()

    app = create_app()

    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

        paths = set(client.get("/openapi.json").json()["paths"].keys())

    expected_paths = {
        "/health",
        "/api/tickets",
        "/api/tickets/{ticket_id}",
        "/api/tickets/{ticket_id}/generate-draft",
        "/api/drafts/{ticket_id}",
        "/api/drafts/{draft_id}",
        "/api/knowledge/ingest",
        "/api/customers/{customer_id}/memories",
        "/api/customers/{customer_id}/memory-search",
    }
    assert expected_paths.issubset(paths)
