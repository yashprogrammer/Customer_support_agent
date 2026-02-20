"""LangChain tools for CRM and billing lookup (mocked)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from langchain_core.tools import tool

from customer_support_agent.repositories.sqlite.customers import CustomersRepository
from customer_support_agent.repositories.sqlite.tickets import TicketsRepository


def _stable_bucket(email: str, size: int) -> int:
    digest = hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()
    return int(digest, 16) % size


def _json(payload: dict[str, Any]) -> str:
    return json.dumps(payload)


def _load_band(open_count: int) -> str:
    if open_count <= 1:
        return "light"
    if open_count <= 3:
        return "moderate"
    return "heavy"


@tool
def lookup_customer_plan(customer_email: str) -> str:
    """Return structured subscription and SLA details for a customer email."""
    plans = [
        {"plan_tier": "free", "sla_hours": 48, "priority_queue": False},
        {"plan_tier": "starter", "sla_hours": 24, "priority_queue": False},
        {"plan_tier": "pro", "sla_hours": 8, "priority_queue": True},
        {"plan_tier": "enterprise", "sla_hours": 1, "priority_queue": True},
    ]
    plan = plans[_stable_bucket(customer_email, len(plans))]
    summary = (
        f"{customer_email} is on the {plan['plan_tier']} plan with "
        f"{plan['sla_hours']}h SLA."
    )
    return _json(
        {
            "tool": "lookup_customer_plan",
            "customer_email": customer_email,
            "summary": summary,
            "details": plan,
            "recommended_action": (
                "Use priority handling." if plan["priority_queue"] else "Use standard handling."
            ),
        }
    )


@tool
def lookup_billing_status(customer_email: str) -> str:
    """Return structured billing status and payment risk details for a customer email."""
    states = [
        {
            "status_code": "good_standing",
            "risk_level": "low",
            "days_overdue": 0,
            "retry_active": False,
            "summary": "Billing is in good standing. Last invoice paid.",
        },
        {
            "status_code": "payment_retry",
            "risk_level": "medium",
            "days_overdue": 0,
            "retry_active": True,
            "summary": "Payment failed once this month. Smart retry is active.",
        },
        {
            "status_code": "overdue",
            "risk_level": "high",
            "days_overdue": 3,
            "retry_active": True,
            "summary": "Invoice overdue by 3 days. Account still active.",
        },
        {
            "status_code": "grace_period",
            "risk_level": "high",
            "days_overdue": 7,
            "retry_active": False,
            "summary": "Trial ended; account in grace period.",
        },
    ]
    state = states[_stable_bucket(customer_email + "billing", len(states))]
    return _json(
        {
            "tool": "lookup_billing_status",
            "customer_email": customer_email,
            "summary": f"Billing status for {customer_email}: {state['summary']}",
            "details": state,
            "recommended_action": (
                "Request billing confirmation in response."
                if state["risk_level"] in {"medium", "high"}
                else "No billing escalation needed."
            ),
        }
    )


@tool
def lookup_open_ticket_load(customer_email: str) -> str:
    """Return structured open-ticket workload details for a customer email."""
    customers_repo = CustomersRepository()
    tickets_repo = TicketsRepository()

    customer = customers_repo.get_by_email(customer_email)
    if not customer:
        return _json(
            {
                "tool": "lookup_open_ticket_load",
                "customer_email": customer_email,
                "summary": f"No customer record found for {customer_email}.",
                "details": {
                    "customer_found": False,
                    "open_tickets": None,
                    "load_band": "unknown",
                },
                "recommended_action": "Ask agent to verify customer email before promising SLA.",
            }
        )

    open_count = tickets_repo.count_open_for_customer(customer_email)
    return _json(
        {
            "tool": "lookup_open_ticket_load",
            "customer_email": customer_email,
            "summary": f"Customer {customer_email} has {open_count} open ticket(s).",
            "details": {
                "customer_found": True,
                "open_tickets": open_count,
                "load_band": _load_band(open_count),
            },
            "recommended_action": (
                "Acknowledge multiple ongoing issues." if open_count > 1 else "Handle as isolated incident."
            ),
        }
    )


def get_support_tools() -> list:
    return [lookup_customer_plan, lookup_billing_status, lookup_open_ticket_load]
