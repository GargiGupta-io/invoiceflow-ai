# Showcase Assets

This file packages the project for applications, short demos, and recruiter-facing summaries.

## One-Line Summary

FastAPI-based LLM finance workflow agent that extracts invoice or finance-email data, routes cases into AP or AR flows, repairs weak retrieval, records guardrailed LLM calls, emits an auditable tool trace, and returns grounded approval actions or follow-up drafts.

## Short Project Summary

This project simulates a compact version of a finance operations AI workflow. A user uploads an invoice or finance-related email, the system extracts structured data through a strict schema, routes the case into accounts payable or accounts receivable logic, retrieves citeable policy context from a synthetic finance knowledge base, repairs missing evidence when retrieval is weak, records each tool-like agent step, and returns a grounded recommendation or drafted action with a human-review gate.

## Demo Setup

From the repo root:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn api.main:app --reload
```

Open:

- `http://127.0.0.1:8000/ui`

## 75-Second Demo Script

### Opening

Say:

```text
This is a finance workflow agent built around two operations use cases: AP invoice review and AR overdue follow-up. The backend is FastAPI-based, uses structured extraction through a guardrails gateway, route-aware retrieval with self-healing repair, tool-call style orchestration, and always returns evidence plus a human-review gate alongside the final action.
```

### AP Flow

Run sample:

- `ap_002_missing_po`

Show:

- extracted structured fields
- route = `accounts_payable`
- anomaly flags
- grounded evidence section
- final recommendation

Say:

```text
This invoice is missing a required PO reference, so the workflow does not guess. It routes the case into AP, pulls the relevant approval and vendor policy, and returns a missing-info recommendation with explicit evidence and review notes.
```

### AR Flow

Run sample:

- `ar_003_payment_claim_no_proof`

Show:

- route = `accounts_receivable`
- escalation triggers
- grounded evidence section
- drafted follow-up email

Say:

```text
For receivables, the same pipeline switches to an AR path. Here the customer claims payment was already made but has not shared proof, so the workflow grounds itself in reminder policy and generates a follow-up asking for the transfer date, transaction reference, and remittance advice.
```

### Close

Say:

```text
The repo also includes a CI-ready evaluation harness over seven synthetic finance cases, so extraction quality, routing accuracy, anomaly coverage, citation support, retrieval repair, human-review gating, tool-call coverage, and latency can be measured rather than assumed.
```

## Recording Checklist

- Use the `/ui` page, not raw API routes
- Keep the browser zoom at `100%`
- Start with the AP sample already selected
- Do not scroll aggressively; keep the route, evidence, and final output visible
- Keep the demo between `60` and `90` seconds
- If you show the terminal, only show startup and one eval command

Optional close-out terminal command:

```powershell
python -m app.eval.run_eval
```

## Resume Bullets

### Default Version

- Built a FastAPI-based finance workflow agent that extracts invoice and finance-email data, routes cases into AP or AR flows, and returns grounded approval recommendations or follow-up drafts.
- Implemented structured LLM extraction, a guardrails gateway, OCR fallback, schema validation, anomaly detection, self-healing route-aware RAG, tool-call tracing, and confidence-based human review.
- Added a CI/CD evaluation gate across seven synthetic finance workflow cases to measure extraction match quality, routing accuracy, citation coverage, grounding support, retrieval repair, anomaly checks, review gates, and latency.

### Metric-Forward Version

- Built a FastAPI-based finance operations agent that achieved `100%` pass rate, workflow-routing accuracy, extraction-field match, citation coverage, and grounding support on the bundled seven-case evaluation set.
- Implemented retrieval over `25` citeable finance-policy chunks plus self-healing RAG repair, schema validation, OCR fallback, tool-call tracing, and anomaly detection for AP and AR workflows.
- Shipped a polished operator UI and CI eval gate so recommendations, evidence, retrieval repair, guardrail metadata, and latency can be inspected end-to-end instead of treated as a black-box model output.

### Short Version

- Built a FastAPI finance workflow agent with structured extraction, self-healing policy RAG, guardrailed LLM calls, tool-call tracing, AP/AR routing, and grounded business-action outputs.
- Added validation, OCR fallback, anomaly detection, human-review gating, and an eval harness for reliability-focused workflow testing.

## Application Blurb

I built this project to simulate the kind of workflow-heavy AI system used in finance operations. Instead of a generic chatbot, it takes invoice or finance-email input, produces strict structured output, retrieves and repairs policy evidence, routes the case into AP or AR logic, records tool-like agent steps, applies a human-review gate, and returns a grounded business action through a FastAPI backend.

## Interview Talking Points

- The routing layer is deterministic so AP vs AR is resolved before downstream reasoning.
- The retrieval layer works over small citeable policy chunks instead of free-form long context, then repairs missing required citations when first-pass retrieval is weak.
- The LLM guardrails gateway centralizes schema-mode calls, fallback behavior, PII-aware redaction, latency, and token metadata.
- The workflow is designed to fail into `missing_info` instead of confidently guessing.
- The audit trail makes the agent workflow inspectable through tool-call records and human-review reasons.
- AP and AR business logic share a policy-assessment layer so anomaly and escalation rules stay maintainable.
- The eval harness makes reliability visible by checking routing, extraction, anomalies, citations, grounding support, retrieval repair, review gates, and latency.

## Honest Caveats

- The dataset is synthetic and intentionally small.
- OCR support is a fallback path and depends on local Tesseract availability.
- AP/AR decision generation is still deterministic; the LLM-heavy path currently focuses on extraction, repair, guardrails metadata, RAG, auditability, and evals.
