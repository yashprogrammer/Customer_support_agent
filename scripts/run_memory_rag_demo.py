"""Single-script demo scenario for Memory + RAG + tools behavior.

Run after backend is up:
    uv run python scripts/run_memory_rag_demo.py
"""

from __future__ import annotations

import os
import time
from typing import Any

import requests

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")


def _request(method: str, path: str, **kwargs: Any) -> Any:
    url = f"{API_BASE}{path}"
    response = requests.request(method, url, timeout=90, **kwargs)
    if response.status_code >= 400:
        raise RuntimeError(f"{method} {path} failed ({response.status_code}): {response.text}")
    return response.json()


def create_ticket(payload: dict[str, Any]) -> dict[str, Any]:
    return _request("POST", "/api/tickets", json=payload)


def generate_draft(ticket_id: int) -> dict[str, Any]:
    return _request("POST", f"/api/tickets/{ticket_id}/generate-draft")["draft"]


def accept_draft(draft_id: int, content: str) -> dict[str, Any]:
    return _request("PATCH", f"/api/drafts/{draft_id}", json={"content": content, "status": "accepted"})


def memory_search(customer_id: int, query: str) -> dict[str, Any]:
    return _request("GET", f"/api/customers/{customer_id}/memory-search", params={"query": query, "limit": 8})


def ingest_knowledge() -> dict[str, Any]:
    return _request("POST", "/api/knowledge/ingest", json={"clear_existing": False})


def run() -> None:
    print("== Ingesting KB (RAG baseline) ==")
    ingest = ingest_knowledge()
    print(f"KB indexed: {ingest['files_indexed']} files / {ingest['chunks_indexed']} chunks")

    customer = {
        "customer_email": "demo.qa.acme@example.com",
        "customer_name": "Priya Sharma",
        "customer_company": "Acme Labs",
    }

    print("\n== Ticket 1: API reliability issue (EU, Shopify, /v1/orders, 429) ==")
    t1 = create_ticket(
        {
            **customer,
            "subject": "EU Shopify sync hitting /v1/orders 429",
            "description": (
                "Priya reports repeated 429 errors on /v1/orders during Shopify sync in EU. "
                "Please verify plan SLA and billing risk."
            ),
            "priority": "high",
            "auto_generate": False,
        }
    )
    d1 = generate_draft(t1["id"])
    print(f"Draft1 length: {len(d1['content'])}")
    d1_accepted = accept_draft(
        d1["id"],
        (
            d1["content"]
            + "\n\nResolution: Enabled backoff using Retry-After for Shopify sync in EU on /v1/orders."
        ),
    )
    print(f"Draft1 accepted: {d1_accepted['status']}")

    print("\n== Ticket 2: Billing + invoice follow-up (same customer) ==")
    t2 = create_ticket(
        {
            **customer,
            "subject": "Invoice PDF failure and retry questions",
            "description": (
                "Same customer asks why invoice PDF downloads fail and if payment retry affects support SLA."
            ),
            "priority": "medium",
            "auto_generate": False,
        }
    )
    d2 = generate_draft(t2["id"])
    print(f"Draft2 length: {len(d2['content'])}")
    d2_accepted = accept_draft(
        d2["id"],
        (
            d2["content"]
            + "\n\nResolution: Guided Priya to Billing > Invoices and confirmed retry status does not pause support."
        ),
    )
    print(f"Draft2 accepted: {d2_accepted['status']}")

    print("\n== Ticket 3: New issue referencing old entities (memory retrieval target) ==")
    t3 = create_ticket(
        {
            **customer,
            "subject": "Priya sees Shopify 429 spikes again",
            "description": (
                "Issue resurfaced for EU traffic. Need response that uses prior context and KB guidance."
            ),
            "priority": "high",
            "auto_generate": False,
        }
    )
    d3 = generate_draft(t3["id"])
    print(f"Draft3 length: {len(d3['content'])}")
    ctx = d3.get("context_used") or {}
    signals = ctx.get("signals") or {}
    print(
        "Draft3 signals => "
        f"memory_hits={signals.get('memory_hit_count')} "
        f"kb_hits={signals.get('knowledge_hit_count')} "
        f"tool_calls={signals.get('tool_call_count')}"
    )

    print("\n== Explicit Memory Probe by entities ==")
    probe = memory_search(t3["customer_id"], "Priya Shopify EU /v1/orders 429")
    print(f"Memory probe results: {len(probe.get('results', []))}")
    for i, hit in enumerate(probe.get("results", [])[:3], start=1):
        snippet = (hit.get("memory") or "").replace("\n", " ")[:180]
        print(f"{i}. {snippet}")

    print("\nDemo complete. Check the Streamlit UI for structured context and memory probe output.")


if __name__ == "__main__":
    run()
