"""Seed sample records and knowledge-base embeddings for local development."""

from __future__ import annotations

from customer_support_agent.core.settings import ensure_directories, get_settings
from customer_support_agent.repositories.sqlite import (
    create_or_get_customer,
    create_ticket,
    init_db,
)
from customer_support_agent.services.copilot_service import SupportCopilot


SAMPLE_CUSTOMERS = [
    {
        "email": "alex@acme.io",
        "name": "Alex Rivera",
        "company": "Acme Labs",
        "tickets": [
            {
                "subject": "Latency spikes on API requests",
                "description": (
                    "We are seeing random latency spikes above 5 seconds on the /v1/orders API. "
                    "This started after yesterday's deploy and affects EU users the most."
                ),
                "priority": "high",
            },
            {
                "subject": "Invoice PDF download failing",
                "description": (
                    "Our finance team cannot download invoice PDFs from the billing portal. "
                    "The button spins forever and eventually times out."
                ),
                "priority": "medium",
            },
        ],
    },
    {
        "email": "maya@northwind.dev",
        "name": "Maya Chen",
        "company": "Northwind",
        "tickets": [
            {
                "subject": "Cannot rotate API key",
                "description": (
                    "When attempting to rotate an API key, the dashboard shows "
                    "'permission denied' even though I am org admin."
                ),
                "priority": "high",
            }
        ],
    },
]


def main() -> None:
    settings = get_settings()
    ensure_directories(settings)
    init_db()

    created_tickets = 0
    for customer_seed in SAMPLE_CUSTOMERS:
        customer = create_or_get_customer(
            email=customer_seed["email"],
            name=customer_seed["name"],
            company=customer_seed["company"],
        )

        for ticket_seed in customer_seed["tickets"]:
            create_ticket(
                customer_id=customer["id"],
                subject=ticket_seed["subject"],
                description=ticket_seed["description"],
                priority=ticket_seed["priority"],
            )
            created_tickets += 1

    print(f"Seeded {len(SAMPLE_CUSTOMERS)} customers and {created_tickets} tickets.")

    try:
        copilot = SupportCopilot(settings=settings)
    except Exception as exc:
        print(f"Skipping KB/memory seed because copilot init failed: {exc}")
        return

    ingest_result = copilot.rag.ingest_directory(
        directory=settings.knowledge_base_path,
        clear_existing=False,
    )
    print(
        "Knowledge base ingest completed: "
        f"{ingest_result['files_indexed']} files, {ingest_result['chunks_indexed']} chunks."
    )

    # Add starter memory so repeat tickets can show personalization in demos.
    copilot.memory.add_interaction(
        user_id="alex@acme.io",
        user_input="Our team often sees latency issues during peak traffic windows.",
        assistant_response=(
            "Thanks for the heads-up. We'll monitor peak-window query times and "
            "recommend autoscaling settings."
        ),
        metadata={"seed": True},
    )
    print("Added 1 sample Mem0 memory for alex@acme.io")


if __name__ == "__main__":
    main()
