# LLM Agent Upgrade Deep Dive

> How InvoiceFlow AI was upgraded from workflow automation into a more explicit LLM-agent system with schema extraction, RAG evidence, tool traces, human review, and evals.

---

## In Plain English

This project already worked like a finance operations assistant. It could read a sample invoice or customer email, pull out important details, decide whether the case belonged to Accounts Payable or Accounts Receivable, retrieve finance-policy context, and return a decision or follow-up draft.

The upgrade made the system more clearly agentic. That means the backend now exposes the steps it took, almost like a receipt. Instead of only saying "missing info" or "send this follow-up email," it records the tool-like actions behind that result: extraction, routing, policy search, duplicate checking, math validation, escalation assessment, email drafting, and audit summary generation.

This matters because strong LLM projects are not just chat interfaces. A real LLM-heavy workflow needs structured outputs, evidence, tool use, review gates, and evaluation. The changes make those ideas visible in the API, UI, documentation, and eval runner.

## What Changed

At a high level, the upgrade added five things:

1. A tool-call style trace for every workflow run.
2. A human-review gate that explains when a case needs manual review.
3. Schema-shaped LLM extraction metadata.
4. More reliable policy evidence selection.
5. Stronger eval metrics for grounding and agent behavior.

The core workflow still stays stable. The existing deterministic baseline remains the default for samples, which means the demo can run without an API key. The LLM path is available when configured, but the repo does not become unusable without one.

## Why This Upgrade Matters

Plain English: before this upgrade, the project could produce good finance workflow outputs, but it did not fully show the "agent" part of the work. Now it shows the chain of reasoning-like operations in a structured, auditable way.

For a resume or interview, this is the difference between saying:

```text
Built a finance automation demo.
```

and saying:

```text
Built an LLM-powered finance workflow agent with structured extraction, RAG,
tool-call tracing, human-review gates, and evals for citation coverage,
grounding support, routing, extraction accuracy, latency, and decision quality.
```

The second version is stronger because it names the actual LLM systems concerns:

- strict schemas
- grounded retrieval
- tool orchestration
- auditability
- confidence and review handling
- evaluation

## Architecture After The Upgrade

Plain English: a document enters the system, gets turned into structured data, gets routed to the correct finance workflow, gets checked against policy, and then the system records what happened before returning the answer.

```text
[Invoice / AR Email / Upload]
          |
          v
[Ingestion Layer]
          |
          v
[Extractor Agent]
          |
          v
[AP/AR Router]
          |
          v
[Policy RAG]
          |
          v
[AP Decision or AR Drafting]
          |
          v
[Agent Tool Trace]
          |
          v
[Human Review Gate]
          |
          v
[Structured API Response + UI + Eval Metrics]
```

Technically, the main orchestration still happens in:

```text
app/orchestrator/engine.py
```

That file runs ingestion, extraction, routing, policy retrieval, decisioning, and audit generation. The new pieces are inserted after the decision is produced:

- `build_agent_tool_trace(...)`
- `build_human_review_gate(...)`

Then the audit trail serializes those results.

## New File: `app/orchestrator/agent_trace.py`

Plain English: this file creates the "receipt" for the workflow. It lists what the agent did, what each step was for, what evidence it used, and whether that step should make a human look twice.

The file introduces two dataclasses:

```python
@dataclass(slots=True)
class AgentToolTrace:
    tool_name: str
    purpose: str
    input_summary: str
    output_summary: str
    evidence_source_ids: list[str]
    confidence_signal: str
    requires_human_review: bool = False
```

Technical detail:

- `tool_name` gives the step a tool-like name.
- `purpose` explains why the step exists.
- `input_summary` records the important input.
- `output_summary` records what came out.
- `evidence_source_ids` links the step to retrieved KB sources.
- `confidence_signal` gives a coarse confidence label.
- `requires_human_review` flags risk at the step level.

The second dataclass is:

```python
@dataclass(slots=True)
class HumanReviewGate:
    required: bool
    reason_codes: list[str]
    reviewer_prompt: str
    blocking: bool
```

Technical detail:

- `required` tells the UI/API whether a person should review.
- `reason_codes` explains why.
- `reviewer_prompt` gives the finance reviewer a concise instruction.
- `blocking` tells whether the workflow should stop until reviewed.

## Tool Trace Behavior

Plain English: AP and AR workflows share the first three tool steps, then each workflow adds its own specialized steps.

Shared steps:

```text
extract_invoice_fields
route_ap_or_ar
search_finance_policy
```

AP-specific steps:

```text
check_duplicate_invoice
validate_invoice_math
create_audit_summary
```

AR-specific steps:

```text
assess_ar_escalation
draft_followup_email
```

This means AP cases usually produce six tool trace entries, while AR cases usually produce five.

## Human Review Gate Behavior

Plain English: the system does not blindly approve risky actions. If a case is missing information, has weak evidence, has low confidence, or requires escalation, it marks the output for human review.

Review can be triggered by:

- low confidence
- missing extracted fields
- missing policy evidence
- AP recommendation of `review`
- AP recommendation of `reject`
- AP recommendation of `missing_info`
- duplicate invoice risk
- missing purchase order
- approval-threshold review
- AR medium/high escalation
- payment claim without proof
- repeated reminder escalation

Blocking review is stricter. It applies when the case should not proceed without human input.

Examples:

- Missing policy evidence is blocking.
- Low confidence is blocking.
- AP `reject` is blocking.
- AP `missing_info` is blocking.
- AR `high` escalation is blocking.

## Audit Trail Changes

Plain English: the API response now carries more of the story behind the final answer.

Before, the audit trail had fields like:

```text
prompt_version
stage_latencies_ms
final_recommendation
evidence_sources
retrieved_chunks
```

After the upgrade, it also includes:

```text
human_review
agent_tool_trace
prompt_applied
```

`prompt_applied` was also improved. It now treats any mode starting with `llm` as prompt-applied, including fallback modes like:

```text
llm_json_object_fallback
```

That matters because older OpenAI-compatible runtimes may not support JSON schema response format, but they can still use a prompt and return JSON.

## LLM Extraction Upgrade

Plain English: when LLM mode is used, the extractor now asks for output shaped like the actual invoice schema instead of only asking for loose JSON.

The key file is:

```text
app/agents/extractor.py
```

The extractor now builds a response format from:

```python
InvoiceExtraction.model_json_schema()
```

Then it requests:

```python
response_format={
    "type": "json_schema",
    "json_schema": {
        "name": "invoice_extraction",
        "schema": schema,
        "strict": False,
    },
}
```

Technical detail:

- This nudges the model toward the exact Pydantic schema.
- Local validation still happens after the LLM response.
- If the runtime rejects JSON schema mode, the code falls back to `{"type": "json_object"}`.
- The fallback is recorded through `last_mode_used`.

This is a practical design because it supports newer structured-output APIs while staying compatible with older JSON-only clients.

## LLM Guardrails Gateway

Plain English: LLM calls now pass through one controlled doorway instead of being scattered directly inside agent code. That doorway can redact obvious sensitive contact data, choose schema response mode, fall back to JSON-object mode, track latency, capture token usage when the provider returns it, and report structured gateway metadata.

The gateway lives in:

```text
app/llm/gateway.py
```

The extractor now uses:

```text
LLMGateway.call_json(...)
```

for both:

- invoice extraction
- extraction repair

The audit trail exposes gateway calls in:

```text
audit_trail.llm_gateway
```

Each gateway metadata record includes:

- purpose
- model
- response format type
- whether fallback was used
- latency in milliseconds
- redaction counts
- prompt tokens, completion tokens, and total tokens when available
- structured error value when parsing or provider behavior fails

This is still a lightweight gateway. It is not a full content-safety platform yet, but it is now a real central control point for LLM calls.

## RAG Retrieval Changes

Plain English: the system now retrieves more policy chunks, then chooses citations more intelligently.

The default retrieval depth changed from:

```python
top_k = 5
```

to:

```python
top_k = 12
```

This helped because the right citation was sometimes present, but ranked just outside the first five results.

However, retrieving more chunks created a new bug. Deeper retrieval brought in unrelated vendors and customers. The simple policy parser could accidentally read those unrelated chunks and overwrite the real vendor/customer policy.

That was fixed in:

```text
app/agents/policy.py
```

The parser now infers the intended source ID from the retrieval query and ignores unrelated vendor/customer chunks.

Example:

```text
vendor Northstar Office Supplies
```

maps to:

```text
VENDOR-001
```

So `extract_vendor_policy()` only applies `VENDOR-001`.

## Evidence Selection Changes

Plain English: the system now chooses citations based on the decision being made, not just whichever chunks ranked highest.

For AP, evidence selection now considers:

- approval recommendation
- anomaly codes
- vendor name

Examples:

- Clean approval should cite `AP-APPROVAL-001`.
- Missing PO should cite `AP-APPROVAL-002`.
- Duplicate invoice should cite `AP-APPROVAL-003`.
- Every AP case should cite `AP-POLICY-003`.
- Vendor-specific cases should cite the matched `VENDOR-*` source.

For AR, evidence selection now considers:

- payment claim status
- escalation level
- customer name

Examples:

- First reminder should cite `AR-TEMPLATE-001`.
- Medium/high escalation should cite `AR-TEMPLATE-003`.
- Payment claim without proof should cite `AR-ESCALATION-002` and `AR-TEMPLATE-004`.
- Customer-specific cases should cite the matched `CUSTOMER-*` source.

## Payment Claim Bug Fix

Plain English: the first-reminder sample said the draft should ask whether payment had already been initiated. The old detector saw that phrase and incorrectly treated the case as if the customer had already claimed payment.

The fix was in:

```text
app/agents/policy.py
```

The phrase:

```text
payment has already been initiated
```

was removed from the generic payment-claim detector.

Now payment-claim handling relies on:

- `document_type == payment_confirmation`
- stronger proof-related markers like transaction reference or remittance proof

This keeps first-reminder cases from accidentally becoming payment-claim exception cases.

## Eval Runner Upgrade

Plain English: the eval suite now measures whether the system is grounded and agent-like, not just whether the final answer matches.

The key file is:

```text
app/eval/run_eval.py
```

New case-level fields:

```text
human_review_required
prompt_applied
agent_tool_count
```

New summary metrics:

```text
grounding_support_pass_rate
human_review_rate
prompt_applied_rate
average_agent_tool_calls
```

The grounding check verifies that cited evidence is actually present in retrieved chunks.

That prevents a subtle failure mode where the final answer cites a source ID that was never retrieved for the current case.

## CI/CD Eval Gate

Plain English: GitHub can now reject changes that make the agent less reliable. Instead of relying on someone to remember to run evals locally, the repo has a workflow that runs the eval suite automatically and fails when key metrics drop.

The new threshold checker lives in:

```text
app/eval/check_eval_thresholds.py
```

It runs the existing eval suite, compares summary metrics against configured thresholds, writes a full JSON report, and exits with status code `1` if any threshold fails. That exit code is what makes CI fail.

The GitHub Actions workflow lives in:

```text
.github/workflows/eval.yml
```

It runs on:

- pushes to `main`
- pull requests
- manual workflow dispatch

The workflow writes and uploads:

```text
eval-results.json
```

The default thresholds require all quality rates to stay at `1.0` on the bundled deterministic eval set, including `rag_repair_success_rate`, plus average latency under `1000` milliseconds.

## Self-Healing RAG

Plain English: retrieval now gets a second chance when the first policy search misses required evidence. The workflow checks which policy sections should be present, compares that list against the first retrieval result, then retries with a query that directly names missing policy IDs.

The repair helper lives in:

```text
app/rag/self_heal.py
```

The policy context builder now does two retrieval stages:

1. A normal first-pass retrieval.
2. A repair retrieval only if required sources are missing.

The repair output is exposed in:

```text
audit_trail.retrieval_repair
```

That payload records:

- whether repair was attempted
- whether repair succeeded
- required source IDs
- missing source IDs before repair
- missing source IDs after repair
- the repair query
- original source IDs
- final source IDs

The eval summary now includes:

```text
rag_repair_attempt_rate
rag_repair_success_rate
```

## UI Upgrade

Plain English: the operator console now shows the agent trace directly, so users do not need to open raw JSON to understand what happened. The latest pass also made the UI feel more like a real product surface: a branded top bar, a large grid-backed hero, reliability callouts, and clearer decision/evidence panels.

Files changed:

```text
web/index.html
web/app.js
web/styles.css
```

The new UI section is:

```text
Agent tool trace
```

For each tool-like step, the UI shows:

- tool name
- output summary
- confidence signal
- whether review is required

The run metadata card also shows:

- tool-call count
- review gate status
- blocking review status when applicable
- self-healing RAG repair status when a repair run happens
- LLM gateway call count when LLM extraction is used

The visual polish intentionally keeps the existing warm finance color scheme. The change is mostly layout, hierarchy, and information architecture rather than a rebrand.

The next refinement opened the page up even more. Instead of keeping the workflow, queue, eval, and advanced areas inside boxed dashboard panels, the layout now uses longer page bands, lighter separators, and a single vertical workflow flow on the main view. That keeps the product readable at a glance without making it feel like a stack of widgets.

The newest pass went one level further and borrowed the reference-style page rhythm: a strong hero, a mid-page thesis band, a numbered flow rail, then the product sections in order. That matters because the page now teaches the product before it starts showing controls, which is closer to a real product site than a dashboard shell.

The latest layout refinement tightened that even more: the header is now centered, the upload chooser lives at the top with an AP/AR hint dropdown, the loading cue appears before the lower workspace opens, and the detail tabs stay hidden until a run completes. That makes the first screen feel like a guided entry point instead of a page full of controls.

## Documentation Upgrade

Plain English: the project now describes itself as an LLM workflow agent instead of just a finance automation demo.

Files changed:

```text
README.md
docs/showcase.md
```

The docs now mention:

- structured LLM extraction
- policy RAG
- tool-call tracing
- human-review gates
- grounding support evals
- prompt-applied metrics
- average agent tool calls

The resume bullets were strengthened to better communicate LLM systems work.

## Final Eval Result

The project venv produced a fully passing eval run:

```json
{
  "total_cases": 7,
  "passed_cases": 7,
  "pass_rate": 1.0,
  "workflow_match_rate": 1.0,
  "extraction_field_match_rate": 1.0,
  "citation_check_pass_rate": 1.0,
  "grounding_support_pass_rate": 1.0,
  "anomaly_check_pass_rate": 1.0,
  "subject_check_pass_rate": 1.0,
  "mention_check_pass_rate": 1.0,
  "human_review_rate": 0.8571,
  "prompt_applied_rate": 0.0,
  "rag_repair_attempt_rate": 1.0,
  "rag_repair_success_rate": 1.0,
  "average_agent_tool_calls": 5.57,
  "average_latency_ms": 10.03
}
```

The `prompt_applied_rate` is `0.0` because the verified run used the default heuristic extractor. That is intentional for local reproducibility. Running with `extractor_mode=llm` and an API key should exercise the prompt path.

## Commands Used For Verification

Plain English: these commands checked that the code imports correctly and the workflow still passes the project's reliability suite.

```powershell
.\.venv\Scripts\python.exe -m compileall app api
```

This checks Python syntax and import-time compilation across the app and API packages.

```powershell
.\.venv\Scripts\python.exe -m app.eval.run_eval
```

This runs the seven-case finance eval suite.

HTTP smoke checks also confirmed:

- `/ui` returns status `200`.
- The page contains the new `Agent tool trace` section.
- `ap_002_missing_po` returns six tool calls.
- `ap_002_missing_po` returns `human_review.required = True`.
- `ap_002_missing_po` returns `recommendation = missing_info`.
- `ap_004_duplicate_invoice` returns `retrieval_repair.attempted = True`.
- `ap_004_duplicate_invoice` returns `retrieval_repair.success = True`.

## Important Tradeoffs

### Deterministic Baseline Remains

Plain English: the project can still run without paid model calls.

Technical detail: sample workflows default to `heuristic` mode. This makes evals reproducible and lets the project demo work locally without `OPENAI_API_KEY`.

### Tool Trace Is Auditable, Not Fake Autonomy

Plain English: the trace shows real backend stages as tool-like steps. It does not pretend an autonomous agent secretly called external tools.

Technical detail: the system translates deterministic workflow stages into a structured agent trace. This is honest and useful for observability, but a future upgrade could add actual LLM tool-calling for selected stages.

### More Retrieval Required Safer Parsing

Plain English: getting more evidence is useful, but only if the system knows which evidence applies.

Technical detail: increasing `top_k` improved citation coverage, but forced tighter vendor/customer filtering in policy extraction.

## What To Say In An Interview

Use this framing:

```text
I started with a deterministic finance workflow so the baseline was reliable.
Then I added the LLM-agent pieces around it: schema-shaped extraction, RAG
evidence, tool-call tracing, human-review gates, and eval metrics. The result
is not just a chatbot; it is an auditable finance workflow agent.
```

If asked why the heuristic path still exists:

```text
The heuristic path is the reproducible baseline. It lets me run evals without
network/model variability. The LLM path is available for extraction, and the
same schema validation, audit trail, review gate, and eval structure apply.
```

If asked about the most interesting bug:

```text
Increasing retrieval depth improved citation coverage but initially caused
unrelated vendor policies to leak into policy parsing. I fixed that by tying
vendor/customer policy extraction to the entity in the retrieval query.
```

## Future Upgrade Path

The strongest next steps are:

1. Add real OCR support for scanned invoices and pasted email screenshots.
2. Add LLM decision drafting behind the existing AP/AR schemas.
3. Add actual tool-calling where the LLM chooses from registered backend tools.
4. Store eval reports as timestamped artifacts and make them downloadable from the UI.
5. Add cost and latency tracking for LLM mode.
6. Add role-based access, reviewer history, and persistent case storage.
7. Add a prompt comparison dashboard in the UI.
8. Add deployment instructions, a public demo URL, and a short demo video.
9. Add multi-tenant support and notification hooks for email, Slack, or Teams.

## Quick Reference

| Concept | Plain English | Project Field/File |
| --- | --- | --- |
| Tool trace | Receipt of what the agent did | `audit_trail.agent_tool_trace` |
| Human review gate | Whether a person should approve the result | `audit_trail.human_review` |
| Grounding support | Cited evidence came from retrieved chunks | `grounding_support_pass_rate` |
| Structured extraction | LLM output shaped like a strict form | `InvoiceExtraction.model_json_schema()` |
| Purpose-aware evidence | Citations chosen for the actual decision | `_required_ap_source_ids`, `_required_ar_source_ids` |
| Deterministic baseline | Local reproducible workflow path | `extractor_mode=heuristic` |
| Prompt-applied rate | How often the LLM prompt path ran | `prompt_applied_rate` |

## Updates

- 2026-05-25 - Updated the UI section after the operator-console polish phase. The repo now documents the brand bar, grid-backed hero, reliability callouts, visible self-healing RAG repair status, LLM gateway call count, and the fresh local verification run on port `8010`.
- 2026-05-28 - Added the evaluation dashboard layer that surfaces dataset size, pass rate, workflow routing accuracy, extraction match, citation coverage, grounding support, AR subject/draft checks, review gate rate, average latency, the latest eval timestamp, and downloadable `eval-results.json` output from the FastAPI app.
- 2026-05-29 - Refined the future-upgrade roadmap so the repo now separates immediate portfolio work from later OCR, persistence, reviewer access, notification, and multi-tenant ideas.
- 2026-05-29 - Added the tabbed workspace shell, AP/AR explainer copy, and pastel accent tuning so the finance console stays input-first while moving review queue, evaluation, and debug content into clearer sections.
- 2026-05-29 - Flattened the tabbed workspace further so the workflow tab reads as open page bands instead of boxed dashboard panels. The workflow, result, trace, and advanced sections now rely on separators and vertical spacing instead of framed cards.
- 2026-05-29 - Reworked the page into a reference-style flow with a manifesto band, numbered section rail, and a linear order for capture, extract, decide, review, evaluate, and inspect.
- 2026-05-29 - Recentered the page around a top upload chooser with AP/AR hinting, a loading cue, three featured demo cases, and a staged reveal where the tabbed workspace appears only after a run completes.

---

*Generated: 2026-05-25 | Project: invoiceflow-ai | Location: docs/llm-agent-upgrade.md*
