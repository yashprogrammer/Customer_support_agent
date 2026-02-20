# Single Test Case: Demonstrate RAG + Mem0 Value

This scenario demonstrates all 4 Mem0-over-RAG value points in one flow.

## Preconditions

1. Backend running:
   - `uv run python main.py`
2. Dashboard running:
   - `uv run streamlit run app.py`
3. `.env` has `GROQ_API_KEY`.

## Run the Scenario

Run:

```bash
uv run python scripts/run_memory_rag_demo.py
```

Or execute manually in the UI.

## What this single case demonstrates

### 1) Entity Relationships

- Ticket 1 and Ticket 2 include entities like `Priya`, `Shopify`, `EU`, `/v1/orders`, `429`, `billing`.
- On accepted drafts, the app saves entity-linked resolution memory.
- In Ticket 3 and memory probe query (`Priya Shopify EU /v1/orders 429`), those linked entities are retrieved together.

Evidence:
- `Memory Probe` in UI returns memories containing linked entities.
- API: `GET /api/customers/{id}/memory-search?query=Priya+Shopify+EU+/v1/orders+429`

### 2) Contextual Continuity Across Sessions

- Tickets use the same customer email (`demo.qa.acme@example.com`).
- Ticket 3 draft uses prior accepted resolutions from Ticket 1 and 2.

Evidence:
- In Ticket 3 draft context: `signals.memory_hit_count > 0`
- Draft content references prior behavior/issues.

### 3) Adaptive Learning From Feedback

- Only `accepted` drafts are written into memory.
- Discarded drafts do not become memory.

Evidence:
- Accepting Ticket 1/2 changes what Ticket 3 retrieves.
- If you discard instead, probe results become weaker.

### 4) Dynamic Updates (vs static RAG)

- RAG KB remains static after ingest.
- Memory changes immediately after each accept and impacts the next draft.

Evidence:
- KB sources in context remain same docs.
- Memory probe results and `memory_hit_count` change after each accepted resolution.

## Pass Criteria

1. Ticket 3 draft has non-empty content.
2. Ticket 3 `context_used.signals.memory_hit_count >= 1`.
3. Ticket 3 `context_used.signals.knowledge_hit_count >= 1`.
4. Memory probe for entity query returns at least one result.
5. Tool calls appear in `context_used.tool_calls`.
