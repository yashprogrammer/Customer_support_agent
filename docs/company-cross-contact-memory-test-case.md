# Single Test Case: Cross-Contact Entity Memory (Same Company)

Goal: prove that Memory (Mem0) carries entity-linked context across two different people from the same company, while RAG remains static.

## Preconditions

1. Backend is running: `uv run python main.py`
2. Dashboard is running: `uv run streamlit run app.py`
3. `.env` has `GROQ_API_KEY`
4. Click `Ingest Knowledge Base` once in UI

## Test Data

Use same company, different contacts:

- Contact A: `priya@acme-labs.com` (Priya Sharma), Company: `Acme Labs`
- Contact B: `rahul@acme-labs.com` (Rahul Nair), Company: `Acme Labs`

Shared entities to track:

- `Shopify`
- `EU`
- `/v1/orders`
- `429`
- `invoice PDF`

## Steps

1. Create Ticket A (Priya)
   - Subject: `EU Shopify sync hits /v1/orders 429`
   - Description: `Priya sees repeated 429 spikes on /v1/orders in EU during Shopify sync. Also invoice PDF timeout appears intermittently.`
2. Generate draft for Ticket A.
3. Accept draft for Ticket A.
   - Before accepting, append this line in draft editor:
   - `Internal note for continuity: entities seen with Priya are Shopify, EU, /v1/orders, 429, invoice PDF timeout.`
4. Create Ticket B (Rahul, same company)
   - Subject: `Following up on Priya's EU 429 issue`
   - Description: `Rahul from same Acme Labs account reports similar Shopify /v1/orders 429 behavior in EU and asks whether invoice PDF timeout is related.`
5. Generate draft for Ticket B.
6. Open `Context used` for Ticket B and verify:
   - `Memory Hits >= 1`
   - `KB Hits >= 1`
7. Run `Memory Probe` on Ticket B with query:
   - `Priya Shopify EU /v1/orders 429 invoice PDF`
8. Verify probe returns at least one hit and includes metadata showing company-scoped memory (`scope: company`).

## Expected Outcome

- Ticket B can retrieve memory from Ticket A even though contact email is different.
- Retrieved memory contains linked entities from Ticket A.
- RAG hits come from static KB docs (same sources as before), while memory content changes immediately after Ticket A acceptance.

## Why this proves Memory > RAG for this case

- Entity relationships: entities are linked and reused across contacts.
- Contextual continuity: continuity is at company level, not just per individual email.
- Adaptive learning: accepted draft content updates memory and influences future drafts.
- Dynamic updates: memory changes immediately after accept, without re-ingesting KB.
