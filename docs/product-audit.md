# Product Audit And Positioning

InvoiceFlow AI should read as one focused product:

> AI-assisted invoice review and receivables follow-up with evidence, audit trails, and human review gates.

The product is not a general chatbot and should not be framed as a pile of AI experiments. Every visible feature should support one of these two finance operations workflows:

- Accounts Payable invoice review
- Accounts Receivable follow-up drafting

## Product Story

In under 10 seconds, a recruiter should understand this:

```text
InvoiceFlow AI helps finance operators review AP invoices and AR follow-up cases.
It extracts structured fields, retrieves policy evidence, recommends the next action,
flags human-review cases, and proves reliability with eval results.
```

## Classification Key

| Label | Meaning |
| --- | --- |
| Core | Directly supports invoice workflow automation or AP/AR decisions. |
| Support | Useful for demos, documentation, evaluation, debugging, or recruiter packaging. |
| Delay | Not needed for the polished portfolio version yet; keep out of the main story. |

## Core Product Surface

| Area | Visible Feature / Module | Classification | Why |
| --- | --- | --- | --- |
| API | `GET /ui` | Core | Main operator console entry point. |
| API | `GET /health` | Core | Confirms the backend is alive for demos and production readiness. |
| API | `GET /samples` | Core | Feeds recruiter-proof AP/AR demo cases. |
| API | `POST /workflow/sample` | Core | Runs deterministic AP/AR sample workflows. |
| API | `POST /workflow/upload` | Core | Runs uploaded document workflows. |
| UI | `web/index.html` | Core | Operator surface for sample, upload, result, evidence, trace, and debug views. |
| UI | `web/app.js` | Core | Drives sample execution, upload execution, result rendering, trace rendering, and metadata display. |
| UI | `web/styles.css` | Core | Product polish for the operator console. |
| Ingestion | `app/ingest/pdf_reader.py` | Core | Reads uploaded PDF/text content before extraction. |
| Ingestion | `app/ingest/ocr.py` | Core | Provides OCR fallback behavior for scanned invoices. |
| Extraction | `app/agents/extractor.py` | Core | Converts document text into structured invoice/customer fields. |
| LLM Gateway | `app/llm/gateway.py` | Core | Centralizes LLM extraction calls, schema format, fallback, redaction metadata, latency, and token metadata. |
| Schemas | `app/schemas/invoice.py` | Core | Defines strict structured extraction output. |
| Schemas | `app/schemas/decision.py` | Core | Defines evidence, AP decisions, AR decisions, and workflow output shape. |
| Routing | `app/orchestrator/router.py` | Core | Separates AP invoice review from AR receivables follow-up. |
| Orchestration | `app/orchestrator/engine.py` | Core | Runs ingestion, extraction, routing, RAG, decisioning, review, and audit flow. |
| Audit | `app/orchestrator/audit.py` | Core | Produces audit trail metadata for trust and traceability. |
| Agent Trace | `app/orchestrator/agent_trace.py` | Core | Shows tool-like workflow steps and human-review reasons. |
| Retrieval | `app/rag/chunker.py` | Core | Converts finance policy docs into citeable sections. |
| Retrieval | `app/rag/embed.py` | Core | Builds deterministic lexical retrieval index for local demo reliability. |
| Retrieval | `app/rag/retrieve.py` | Core | Retrieves ranked policy evidence for decisions. |
| Retrieval Repair | `app/rag/self_heal.py` | Core | Repairs missing required policy evidence before decision output. |
| Research Agent | `app/agents/research.py` | Core | Builds grounded policy context for AP/AR flows. |
| Policy Agent | `app/agents/policy.py` | Core | Interprets retrieved evidence into AP/AR policy assessment. |
| AP Agent | `app/agents/decision.py` | Core | Produces AP recommendations, anomalies, evidence, and reviewer summary. |
| AR Agent | `app/agents/editor.py` | Core | Produces AR escalation level, subject, follow-up draft, and evidence. |
| TTS Formatting | `app/agents/tts.py` | Core | Makes AR follow-up text safer to read aloud and demo clearly. |
| Knowledge Base | `kb/approval_matrix.md` | Core | Approval policy source for AP decisions. |
| Knowledge Base | `kb/invoice_policy.md` | Core | Invoice validation policy source. |
| Knowledge Base | `kb/reminder_templates.md` | Core | AR reminder and escalation policy source. |
| Knowledge Base | `kb/vendor_terms.md` | Core | Vendor/customer-specific policy source. |
| Samples | `samples/invoices/*` | Core | AP demo cases for missing PO, duplicate invoice, threshold review, and clean invoice. |
| Samples | `samples/emails/*` | Core | AR demo cases for first follow-up, escalation, and payment-claimed-without-proof. |
| Expected Outputs | `samples/expected_outputs/*` | Core | Ground truth for evals and workflow confidence. |

## Support Surface

| Area | Visible Feature / Module | Classification | Why |
| --- | --- | --- | --- |
| Evaluation | `app/eval/run_eval.py` | Support | Proves routing, extraction, evidence, anomaly, AR copy, review gate, latency, and repair quality. |
| Evaluation | `app/eval/check_eval_thresholds.py` | Support | Turns evals into a CI quality gate. |
| Evaluation | `app/eval/dataset.json` | Support | Defines cases used to validate product reliability. |
| Evaluation | `.github/workflows/eval.yml` | Support | Shows engineering discipline through automated eval checks. |
| Prompt Audit | `app/eval/prompt_ab.py` | Support | Useful for technical review of prompt versions, but not a primary user workflow. |
| Prompts | `app/prompts/extractor_v1.md` | Support | Supports LLM extraction behavior. |
| Prompts | `app/prompts/extractor_v2.md` | Support | Supports prompt comparison. |
| Prompts | `app/prompts/extractor_repair_v1.md` | Support | Supports LLM repair path. |
| Docs | `README.md` | Support | Main recruiter-facing explanation and setup guide. |
| Docs | `docs/showcase.md` | Support | Demo script, resume bullets, and interview framing. |
| Docs | `docs/llm-agent-upgrade.md` | Support | Deep technical explanation of LLM/RAG/eval upgrades. |
| Docs | `docs/learning-guide.md` | Support | Learning reference, useful but secondary to the product story. |
| Docs | `docs/screenshots/*` | Support | Visual proof for README and portfolio. |
| Project Metadata | `requirements.txt` | Support | Environment setup. |
| Project Metadata | `app/__init__.py` | Support | Package metadata. |
| Package Files | `__init__.py` files | Support | Python package wiring. |
| Knowledge Base Index | `kb/index.json` | Support | Generated retrieval index; important for runtime but not a feature to market. |
| Sample Docs | `samples/README.md` and `samples/expected_outputs/README.md` | Support | Explain fixture structure for maintainers. |

## Delay Surface

| Area | Visible Feature / Module | Classification | Why |
| --- | --- | --- | --- |
| Old Planning | `docs/archive/build-history.md` | Delay | Useful build history, now archived away from the main product surface with a clear InvoiceFlow AI framing note. |
| Prompt A/B UI | Public prompt comparison dashboard | Delay | Useful later, but not needed before AP/AR operator flow is polished. Keep prompt comparison as backend/CLI support for now. |
| Live LLM Decisioning | LLM-generated AP/AR decisions | Delay | Current deterministic AP/AR decisions are safer for demo reliability. Add later behind existing schemas and review gates. |
| Cost Dashboard | Per-run cost display | Delay | Token metadata exists when available, but a full cost dashboard can wait until live LLM usage is central. |
| Persistent Database | Case history storage | Delay | Useful product feature, but local deterministic samples are enough for portfolio polish. |
| Role-Based Access | Reviewer accounts and permissions | Delay | Real product feature, but too much scope before recruiter-ready demo flow. |
| Integrations | Email, Slack, Teams, ERP, accounting systems | Delay | Future roadmap only; not needed for the focused portfolio version. |

## Main Story To Preserve

Everything above the fold in the app and README should reinforce this sequence:

```text
Input document or sample
  -> structured extraction
  -> AP/AR routing
  -> policy retrieval with citations
  -> validation and anomaly checks
  -> decision or follow-up draft
  -> human review gate
  -> audit trail and eval metrics
```

## What To Emphasize

- AP invoice review and AR follow-up are the only two main workflows.
- Evidence is visible near the recommendation.
- Risky or weakly grounded outputs require human review.
- The demo works without paid API keys through deterministic fixtures.
- Eval results are product evidence, not hidden terminal-only tooling.

## What To De-Emphasize

- Generic AI assistant language.
- Historical build notes as primary product documentation.
- Prompt experimentation as a product feature.
- OCR as a guaranteed production feature when the local environment may not have Tesseract.
- Future integrations before the operator workflow is polished.

## Phase 1 Positioning Decision

The portfolio version should present InvoiceFlow AI as:

```text
A finance operations console for AP invoice review and AR follow-up drafting,
with structured extraction, grounded policy evidence, human review gates,
audit metadata, and visible eval quality.
```

That is the story future phases should enforce in the UI, README, screenshots, tests, and demo path.
