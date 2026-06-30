# InvoiceFlow AI

AI-assisted invoice review and receivables follow-up for finance teams.

InvoiceFlow AI helps operations teams review AP invoices, detect missing or
risky information, retrieve policy evidence, draft AR follow-ups, and route
uncertain cases to human review with a full audit trail.

I originally built InvoiceFlow AI as a YC-style product prototype for finance
workflow automation, then expanded it into a general AI operations project
focused on invoice review, AR follow-ups, policy evidence, and audit trails.

The product promise is simple:

```text
Select or upload an invoice/AR case
  -> extract key facts
  -> check policy evidence
  -> detect risk
  -> recommend an action
  -> route uncertain cases to human review
  -> preserve an audit trail
```

Review faster. Decide with evidence. Escalate safely.

## The Problem

Finance teams spend time manually checking invoices, matching policy rules,
identifying missing purchase orders, reviewing payment terms, and writing
follow-up emails for overdue invoices.

Generic AI chat tools are not enough because finance workflows need structure,
evidence, repeatability, and human approval. A finance operator needs to know
what action to take, why that action is supported, and when a person should
review the case before anything moves forward.

## What InvoiceFlow Does

InvoiceFlow turns invoice and receivables work into a reviewable workflow:

```text
Input
  -> extracted facts
  -> AP/AR route
  -> policy evidence
  -> risk checks
  -> recommendation or draft
  -> human review gate
  -> audit trail
```

| Input | Output |
| --- | --- |
| Invoice PDF | Extracted vendor, invoice number, amount, due date, PO status, payment terms, and line items. |
| Invoice text | AP workflow route, missing-field checks, anomaly list, policy evidence, and recommendation. |
| Overdue invoice case | AR route, escalation level, safe follow-up subject, and follow-up draft. |
| Customer finance email | Payment-claim checks, missing-proof flags, reminder guidance, and review status. |
| Finance policy documents | Retrieved policy evidence with source names, citation IDs, and decision influence. |
| Workflow result | Confidence/risk summary, human review decision, tool trace, audit metadata, and raw JSON for debugging. |

## Best Demo Path

Use this path when showing the project to a recruiter, client, or technical
reviewer:

1. Open the operator console at `/ui`.
2. Select the `Missing PO Invoice` sample.
3. Review the extracted invoice fields.
4. Check the final recommendation.
5. Open the policy evidence panel.
6. Review the anomaly list and "Why this decision?" explanation.
7. Send the case to human review.
8. Open the compact audit trail.
9. Run the `AR Overdue Follow-Up` sample.
10. Show the drafted follow-up email and escalation reasoning.

## Safety And Privacy

InvoiceFlow is designed as an evidence-backed assistant, not an unchecked
autopilot.

- No raw API keys are committed.
- Demo mode uses bundled sample data by default.
- Uploaded files are processed for the current workflow run.
- Recommendations are shown with policy evidence and audit metadata.
- Low-confidence, risky, or weakly grounded cases route to human review.
- Raw model/debug outputs stay behind advanced inspection views.
- The audit trail records decision metadata, tool trace steps, retrieved
  evidence, review-gate status, latency, and prompt metadata when available.

## Demo Mode And Live AI Mode

The project is built so the main demo does not break without paid API keys.

| Mode | What it does | When to use |
| --- | --- | --- |
| Demo mode | Uses deterministic sample fixtures, local policy retrieval, AP/AR logic, evidence, review gates, and evals. | Portfolio demos, recruiter walkthroughs, local testing, and deployment without secrets. |
| Live AI mode | Uses the configured LLM path for schema-shaped extraction and repair metadata when credentials are available. | Technical review of LLM extraction, guardrails, prompt versions, and runtime metadata. |

## How This Can Be Adapted For A Client

InvoiceFlow can be customized for:

- company-specific invoice approval policies
- vendor-specific purchase-order rules
- duplicate invoice detection logic
- ERP or accounting export formats
- AR reminder and escalation templates
- approval workflows and reviewer queues
- Slack, Teams, or email notifications
- CSV exports and finance reporting
- department-specific audit requirements

## What This Project Demonstrates

- AI workflow orchestration
- document ingestion and structured extraction
- retrieval-augmented policy evidence
- schema validation and repair-aware extraction
- AP invoice review logic
- AR follow-up drafting logic
- human-in-the-loop review design
- audit-friendly AI outputs
- FastAPI backend development
- frontend operator-console design
- evaluation-driven AI development
- CI/CD quality gating for AI workflows
- production-aware failure handling

## Technical Review

The sections below are for reviewers who want implementation details after the
product story is clear.

## Product Snapshot

```text
Input invoice or AR case
  -> structured extraction
  -> AP/AR routing
  -> policy evidence retrieval
  -> validation and anomaly checks
  -> recommendation or follow-up draft
  -> human review gate
  -> audit trail and eval metrics
```

## Core Workflows

The product supports two focused finance workflows:

### Accounts Payable
- ingest an invoice document
- extract structured fields
- retrieve approval and vendor policy context
- return one of:
  - `approve`
  - `review`
  - `reject`
  - `missing_info`

### Accounts Receivable
- ingest an overdue invoice case or customer finance email
- retrieve reminder and escalation guidance
- draft a grounded follow-up email
- return an escalation level plus evidence

## Why This Project Exists

This repo is intentionally shaped around workflow-heavy finance operations, not
generic chat. The main story is:

- AP invoices should be reviewed against policy before payment.
- AR follow-ups should be drafted from case data without aggressive or unsupported escalation.
- Risky, missing, or weakly grounded cases should route to human review.
- Recommendations should be backed by citations, audit metadata, and eval results.

## Quick Look

### Console Overview

![InvoiceFlow AI console overview](docs/screenshots/console-overview.png)

### AP Result Walkthrough

![InvoiceFlow AI AP result view](docs/screenshots/ap-missing-po-result.png)

## Implementation Snapshot

Implemented:
- sample and upload ingestion
- PDF parsing with OCR fallback hooks
- strict extraction schema
- deterministic development extractor
- LLM extraction path with schema-shaped JSON responses and validation repair
- LLM guardrails gateway for schema-mode fallback, PII-aware request redaction, latency metadata, and token metadata when available
- retrieval-ready finance knowledge base
- policy retrieval with citations
- explicit tool-call style agent trace for extraction, routing, policy search, validation, and action generation
- AP vs AR routing
- AP decision flow
- AR drafting flow
- confidence-based human review gate for risky, low-evidence, or missing-information cases
- TTS-safe AR follow-up variants for dates, amounts, and identifiers
- workflow audit trail with prompt version, stage timings, retrieved chunks, and final action
- shared anomaly and escalation assessment
- FastAPI backend
- operator UI at `/ui`
- polished operator-console layout with brand bar, grid-backed hero, reliability callouts, and decision/evidence panels
- evaluation dataset and runner
- CI/CD eval threshold gate for reliability regressions
- clean smoke-test run in a separate virtual environment

Still worth improving:
- production-grade OCR/runtime setup
- live deployment and final demo recording
- LLM-based AP/AR decision drafting behind the existing schemas
- cost and token tracking for LLM mode

## Technical Architecture

```text
[Document Input: PDF / text / email fixture]
                  |
                  v
         [Ingestion Layer]
                  |
                  v
         [Extractor Agent]
                  |
                  v
         [Workflow Router]
                  |
          +-------+-------+
          |               |
          v               v
 [Grounded Policy Context] [Grounded Policy Context]
          |               |
          v               v
   [AP Decision Flow]   [AR Drafting Flow]
          |               |
          +-------+-------+
                  |
                  v
 [Tool Trace + Human Review Gate]
                  |
                  v
      [Structured Result + Evidence]
```

## Workflow Logic

### AP Flow

Input:
- invoice PDF or text fixture
- vendor-specific policy context

Checks:
- missing required invoice fields
- purchase order requirement
- duplicate invoice hints
- payment terms mismatch
- approval threshold
- invalid/void invoice wording
- line-item total mismatch

Output:
- recommendation
- anomaly list
- reviewer summary
- cited evidence

### AR Flow

Input:
- overdue invoice case or customer reply
- customer tone and escalation context

Checks:
- overdue-day band
- prior reminder count
- payment-claimed-without-proof case
- missing due date / invoice number
- escalation trigger set

Output:
- escalation level
- subject line
- follow-up email draft
- TTS-safe subject and follow-up draft
- cited evidence

## Repository Layout

```text
invoiceflow-ai/
|- api/
|  `- main.py
|- docs/
|  `- showcase.md
|- app/
|  |- agents/
|  |- eval/
|  |- ingest/
|  |- orchestrator/
|  |- prompts/
|  |- rag/
|  `- schemas/
|- kb/
|- samples/
|  |- emails/
|  |- expected_outputs/
|  `- invoices/
`- web/
```

## Showcase Assets

- `docs/showcase.md` contains the demo script, recorder checklist, resume bullets, and application blurb for this project.

## Quick Start

From the project root:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn api.main:app --reload
```

Then open:

- API root: `http://127.0.0.1:8000/`
- Operator UI: `http://127.0.0.1:8000/ui`

## Technical UI And API Reference

### UI

Use `/ui` to:
- start from the operator entry screen with `Run AP Sample`, `Run AR Sample`, `Upload Invoice`, and `View Evaluation`
- inspect the first-screen snapshot for workflow state, AP/AR sample count, upload readiness, latest audit summary, and eval pass rate
- run built-in sample workflows from the hero buttons, quick sample chips, or sample selector
- upload a local invoice or finance document
- inspect the workflow path, key document fields, final action, anomalies/triggers, and evidence
- inspect latency, prompt-version metadata, self-healing RAG repair status, and LLM gateway call count
- inspect the tool-call trace without opening raw JSON
- open the full backend response only when needed through the collapsible debug panel

For screenshots or quick demos, the UI also supports:

- `/ui?sample=ap_002_missing_po&mode=heuristic&autorun=1`
- `/ui?sample=ar_003_payment_claim_no_proof&mode=heuristic&autorun=1`

### API Routes

- `GET /`
- `GET /ui`
- `GET /health`
- `GET /samples`
- `POST /workflow/sample`
- `POST /workflow/upload`

<details>
<summary>Workflow response metadata</summary>

Workflow responses include:

- `audit_trail.requested_extractor_mode`
- `audit_trail.effective_extractor_mode`
- `audit_trail.prompt_version`
- `audit_trail.prompt_applied`
- `audit_trail.llm_gateway`
- `audit_trail.retrieval_repair`
- `audit_trail.stage_latencies_ms`
- `audit_trail.total_latency_ms`
- `audit_trail.final_recommendation`
- `audit_trail.human_review`
- `audit_trail.agent_tool_trace`
- `audit_trail.evidence_sources`
- `audit_trail.retrieved_chunks`

</details>

### Sample Run

The UI focuses on these five demo cases:

| UI case | Sample ID | Expected result |
| --- | --- | --- |
| Clean Invoice | `ap_001_clean_invoice` | `approve` |
| Missing PO Invoice | `ap_002_missing_po` | `missing_info` |
| Duplicate Invoice Risk | `ap_004_duplicate_invoice` | `review` |
| High-Value Approval Required | `ap_003_threshold_review` | `review` |
| AR Overdue Follow-Up | `ar_003_payment_claim_no_proof` | `draft_follow_up` |

## Evaluation Proof

Run the built-in evaluation suite from the repo root:

```bash
python -m app.eval.run_eval
```

Run the CI-style threshold gate locally:

```bash
python -m app.eval.check_eval_thresholds --output eval-results.json
```

The eval runner checks:
- workflow-type match
- extraction field match rate
- AP/AR final decision match
- citation coverage
- grounding support for cited evidence
- anomaly coverage
- AR subject coverage
- AR draft mention coverage
- human-review gate rate
- average agent tool calls
- prompt-applied rate for LLM runs
- case latency

<details>
<summary>Technical prompt audit</summary>

```bash
python -m app.eval.prompt_ab
```

This support script:
- compares `extractor_v1` vs `extractor_v2`
- always runs a structural prompt audit
- runs dataset-level runtime comparison too when `OPENAI_API_KEY` is configured

It is not part of the main operator workflow. The product demo should stay focused on AP review, AR follow-up, evidence, human review, and eval quality.

</details>

The current heuristic baseline already shows:
- `100%` workflow-routing accuracy on the bundled eval set
- `100%` extraction-field match on the bundled eval set
- `100%` citation coverage and grounding support on the bundled eval set
- review-gate and tool-trace metrics for agent observability

## CI/CD Eval Gate

GitHub Actions runs `.github/workflows/eval.yml` on pushes, pull requests, and
manual dispatches. The workflow installs dependencies, runs the eval threshold
gate, fails the build if quality drops below configured minimums, and uploads
`eval-results.json` as an artifact for inspection.

<details>
<summary>Default CI thresholds</summary>

Default CI thresholds require:

- `pass_rate >= 1.0`
- `workflow_match_rate >= 1.0`
- `extraction_field_match_rate >= 1.0`
- `citation_check_pass_rate >= 1.0`
- `grounding_support_pass_rate >= 1.0`
- `anomaly_check_pass_rate >= 1.0`
- `subject_check_pass_rate >= 1.0`
- `mention_check_pass_rate >= 1.0`
- `rag_repair_success_rate >= 1.0`
- `average_latency_ms <= 1000`

</details>

## Known Limitations

- The local environment still needs dependencies installed to run the full stack
  normally.
- OCR fallback depends on Tesseract being installed on the host machine.
- The `heuristic` extractor path is intentionally tuned for the sample fixtures.
- The `llm` extractor/repair path requires an OpenAI-compatible API key and
  runtime configuration.
- The guardrails gateway currently covers LLM extraction and repair calls; AP/AR
  decision generation is still deterministic.
- TTS-safe output is currently implemented for AR follow-up text only.
- The UI is a local operator console, not a deployed production dashboard.

## Next Improvements

- add real OCR support for scanned invoices using Tesseract or a hosted OCR service
- add role-based access for reviewers and operators
- add a persistent case store with approval history and audit lookups
- add vendor risk scoring and a PDF annotation view for invoice review
- add email, Slack, and Teams notifications for escalations
- add multi-tenant organization support
- add cost tracking for LLM calls and per-case runtime metadata
- add real tool-calling agent behavior after the current deterministic baseline
- record a short demo video and a hosted demo URL for portfolio sharing
