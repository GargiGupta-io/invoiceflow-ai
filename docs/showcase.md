# Showcase Assets

This file packages the project for applications, short demos, and recruiter-facing summaries.

## One-Line Summary

InvoiceFlow AI is a finance operations console for AP invoice review and AR follow-up drafting, with structured extraction, policy evidence, audit trails, human review gates, and eval-backed reliability.

## Short Project Summary

InvoiceFlow AI helps a finance operator decide what to do with an invoice or overdue payment case. A user runs an AP or AR sample, uploads a document, or reviews pasted finance text. The system extracts structured fields, routes the case into Accounts Payable or Accounts Receivable, retrieves citeable policy evidence, repairs missing evidence when retrieval is weak, records each tool-like step, and returns a grounded recommendation or follow-up draft with a human-review gate.

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

## Best Demo Path

Use this path when showing the project to a recruiter, client, or technical reviewer:

1. Open `http://127.0.0.1:8000/ui`.
2. Start at the centered operator entry screen and point out the product promise: review faster, decide with evidence, escalate safely.
3. Explain AP and AR in plain English:
   - AP reviews vendor invoices before payment.
   - AR follows up on overdue customer payments.
4. Run `Missing PO Invoice`.
5. Read the decision-first result: recommendation, reason, confidence/risk, evidence count, and human review status.
6. Open `Evidence & Reasoning` and show the policy match, extracted fields, anomalies, and "Why this decision?" checklist.
7. Open `Human Review & Audit` and show that risky cases do not get treated as final.
8. Run `AR Overdue Follow-Up`.
9. Show the drafted follow-up and why escalation is justified.
10. Open `Evaluation` and show the compact reliability proof.

## 75-Second Demo Script

### Opening

Say:

```text
This is InvoiceFlow AI, a finance operations console for two common workflows: AP invoice review and AR overdue follow-up. The product promise is simple: upload or select a case, extract the facts, check policy evidence, detect risk, recommend an action, and keep a human-review trail.
```

Then say:

```text
AP means reviewing vendor invoices before payment. AR means following up on overdue customer payments. The app keeps both workflows in one clear path without making the operator read raw model output first.
```

### AP Flow

Run `Missing PO Invoice`.

Show:

- final recommendation: `Request Missing Info`
- reason: purchase order is required but no PO was found
- confidence/risk
- evidence count
- human review status

Say:

```text
This invoice is missing a required PO reference, so InvoiceFlow does not guess or approve blindly. It asks for the missing information, shows the policy evidence, and routes the case to human review before payment continues.
```

Open `Evidence & Reasoning`.

Show:

- extracted invoice fields
- policy evidence
- anomalies
- "Why this decision?" checklist
- agent trace

Say:

```text
The important part is explainability. The decision is not just "AI says review." The page shows PO required, PO found, invoice amount, approval threshold, matching policy, risk level, and review status.
```

Open `Human Review & Audit`.

Say:

```text
Risky outputs are not treated as final. The review queue and audit trail show why a person needs to inspect the case and what the workflow did before the recommendation was shown.
```

### AR Flow

Run `AR Overdue Follow-Up`.

Show:

- route = Accounts Receivable
- overdue/payment-claim context
- escalation reason
- drafted follow-up email

Say:

```text
For receivables, the same workflow switches to an AR path. Here the customer claims payment was already made but has not shared proof, so InvoiceFlow drafts a professional follow-up asking for the transfer date, transaction reference, and remittance advice.
```

### Evaluation Proof

Open `Evaluation`.

Say:

```text
The evaluation tab is deliberately secondary. It proves the workflow is checked across routing, extraction, citation coverage, grounding, anomaly detection, review gates, AR draft safety, and latency without turning the product into an academic dashboard.
```

### Close

Say:

```text
The repo is designed to show both product thinking and engineering depth: a finance manager can understand the workflow quickly, while a technical reviewer can inspect retrieval, guardrails, audit metadata, and evaluation results.
```

## Recording Checklist

- Use the `/ui` page, not raw API routes
- Keep the browser zoom at `100%`
- Start from the centered operator entry screen
- Keep the five-case selector visible before running a case
- Do not scroll aggressively; keep the recommendation, evidence, and review gate visible
- Keep the demo between `60` and `90` seconds
- Keep raw JSON/debug collapsed unless the viewer is technical
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

I built this project to simulate a finance operations console, not a generic chatbot. It takes invoice or finance-email input, produces strict structured output, retrieves and repairs policy evidence, routes the case into AP or AR logic, records tool-like agent steps, applies a human-review gate, and returns a grounded business action through a FastAPI backend.

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
