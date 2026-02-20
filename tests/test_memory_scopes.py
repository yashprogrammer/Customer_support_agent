"""Regression tests for company-scoped memory behavior."""

from __future__ import annotations

from customer_support_agent.services.copilot_service import SupportCopilot


def test_memory_scope_ids_include_customer_and_company() -> None:
    copilot = object.__new__(SupportCopilot)

    scope_ids = copilot._memory_scope_ids(
        customer_email="ALEX@ACME.IO",
        customer_company="Acme Labs",
    )

    assert scope_ids[0] == "alex@acme.io"
    assert "company::acme-labs" in scope_ids


def test_dedupe_memory_hits_is_case_insensitive() -> None:
    hits = [
        {"memory": "EU 429 on /v1/orders"},
        {"memory": "eu 429 on /v1/orders"},
        {"memory": "Invoice PDF timeout in portal"},
    ]

    deduped = SupportCopilot._dedupe_memory_hits(hits, limit=10)

    assert len(deduped) == 2
