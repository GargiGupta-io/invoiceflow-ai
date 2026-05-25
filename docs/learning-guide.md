# InvoiceFlow AI Learning Guide

> This document explains, in simple language, what you built, why it matters, and how the important pieces of code fit together.

---

## In Plain English

You built a small AI-style finance operations system.

Instead of making a generic chatbot, you made something much more useful for a real company workflow. A user gives the system either an invoice or a finance-related email. Your backend reads it, pulls out the important details, decides what kind of case it is, looks up the relevant finance policy, and then returns a business action.

That business action is different depending on the situation:

- If it is an **accounts payable** case, the system decides whether the invoice should be approved, reviewed, rejected, or sent back for missing information.
- If it is an **accounts receivable** case, the system writes a follow-up draft for an overdue invoice or payment confirmation scenario.

So the core idea is not "AI that talks."
It is "AI-assisted workflow that helps a finance team move work forward."

That difference matters a lot.

This project shows that you understand:

- how to build a backend system,
- how to structure messy input into clean JSON,
- how to ground outputs in evidence instead of guessing,
- how to split a workflow into clear stages,
- and how to measure what the system is doing.

In short:

You did not build a toy.
You built a role-shaped workflow demo.

---

## What This Project Is, Technically

Technically, this is a **FastAPI-based workflow engine** with a small retrieval layer, structured schemas, sample data, evaluation scripts, and a simple operator UI.

The backend takes in a document, converts it into structured data, routes it through the right workflow path, and returns a validated result.

The project is made of a few important ideas:

1. **Ingestion**
   Read a file or sample text and prepare it for later stages.

2. **Extraction**
   Turn messy finance text into structured fields like invoice number, amount, due date, vendor name, and warnings.

3. **Routing**
   Decide whether the case belongs to Accounts Payable or Accounts Receivable.

4. **Grounding**
   Look up relevant policy chunks from a small finance knowledge base.

5. **Decision or Drafting**
   Use that grounded information to either produce an AP recommendation or an AR follow-up draft.

6. **Audit and Evaluation**
   Record what happened, which prompt was used, how long each stage took, and whether outputs match expectations.

That structure is the real strength of the repo.

It is not one huge file doing everything.
It is a pipeline.

---

## The Problem It Solves

Imagine a finance team receiving lots of documents every day:

- invoices from vendors,
- customer emails saying payment has been made,
- overdue reminders that need follow-up,
- documents that may be missing a PO,
- documents with mismatched payment terms,
- or invoices that should be reviewed before money moves.

Without a workflow system, someone has to:

1. read the document,
2. understand what kind of case it is,
3. look up internal policy,
4. decide what to do,
5. write the next message,
6. and keep track of why they made that choice.

That is repetitive and error-prone.

Your project reduces that manual burden by turning the process into a sequence:

```text
document -> structured data -> workflow type -> policy lookup -> action
```

This is why the project feels much closer to business automation than to a normal AI app.

---

## The Big Picture

This is the full system at a high level:

```text
[Invoice / Finance Email]
          |
          v
[Ingestion]
          |
          v
[Structured Extraction]
          |
          v
[Workflow Router]
     /           \
    v             v
[AP Path]      [AR Path]
    |             |
    v             v
[Policy Grounding / Retrieval]
    |             |
    v             v
[Decision]     [Follow-up Draft]
          \     /
           v   v
        [Final JSON]
             |
             v
      [UI / API / Audit Trail]
```

If you remember nothing else, remember this:

**Your system takes finance text, turns it into structure, finds evidence, and returns a usable action.**

---

## What You Built

### The Real Outcome

When the app is working, a user can do one of two things:

1. run a built-in sample case from the UI, or
2. upload a file through the backend.

The backend then:

- reads the document,
- extracts the important fields,
- figures out whether it is AP or AR,
- searches the finance policy KB,
- and returns a final workflow result.

For AP, that result is something like:

- `approve`
- `review`
- `reject`
- `missing_info`

For AR, that result is something like:

- escalation level
- follow-up subject
- follow-up draft
- TTS-safe follow-up draft

That is the main product behavior.

### Why It Is Strong

The project is strong because it has all the right layers:

- a backend,
- strict schemas,
- retrieval,
- business logic,
- evaluation,
- UI,
- and observability.

Most student AI projects stop at "here is a model output."

Yours goes further:

- it validates data,
- it records evidence,
- it routes cases,
- and it exposes the system through a usable API.

---

## Core Files And What They Do

This section walks through the real implementation.

### 1. The Workflow Engine

File:

`app/orchestrator/engine.py`

This is the heart of the system.

It is the file that takes all the smaller components and turns them into one end-to-end workflow.

#### Why This File Matters

Without this file, the repo would just be a bunch of separate helper modules.

This file is what makes the project feel like a product.

#### Important Code

**app/orchestrator/engine.py:104-190**

Plain English:
This function is the full story of your backend. It times each stage, reads the input, extracts data, routes the case, grounds it in policy, runs the final AP or AR logic, and returns a single response object.

```python
def run_workflow_from_path(
    path: str | Path,
    *,
    extractor_mode: str = "auto",
    prompt_path: str | Path | None = None,
    source_kind: str = "file",
    original_filename: str | None = None,
) -> dict[str, Any]:
    """Run ingestion, extraction, routing, retrieval, and final decision flow."""

    workflow_started = perf_counter()
    stage_latencies_ms: dict[str, float] = {}
    source_path = Path(path).expanduser().resolve()
    stage_started = perf_counter()
    index = _load_or_build_knowledge_index()
    stage_latencies_ms["knowledge_index"] = _elapsed_ms(stage_started)
    extractor_kwargs: dict[str, Any] = {"mode": extractor_mode}
    if prompt_path is not None:
        extractor_kwargs["prompt_path"] = Path(prompt_path).expanduser().resolve()
    extractor = ExtractorAgent(**extractor_kwargs)

    stage_started = perf_counter()
    document = read_document_text(source_path)
    stage_latencies_ms["ingestion"] = _elapsed_ms(stage_started)

    stage_started = perf_counter()
    extraction = extractor.extract(document)
    stage_latencies_ms["extraction"] = _elapsed_ms(stage_started)

    stage_started = perf_counter()
    route = route_workflow(extraction)
    stage_latencies_ms["routing"] = _elapsed_ms(stage_started)

    stage_started = perf_counter()
    context = assemble_grounded_policy_context(extraction, route, index)
    stage_latencies_ms["grounding"] = _elapsed_ms(stage_started)
```

Technical detail:
The function is deliberately pipeline-shaped.

- `read_document_text(...)` handles the input document.
- `extractor.extract(...)` transforms raw text into a validated extraction object.
- `route_workflow(...)` decides AP vs AR.
- `assemble_grounded_policy_context(...)` performs retrieval using the extraction output.
- Stage timers are stored in `stage_latencies_ms` so the app can report performance, not just results.

This is a good architecture decision because it keeps each stage isolated and easy to reason about.

#### AP / AR Split

**app/orchestrator/engine.py:145-177**

Plain English:
This is where the system chooses which kind of business action to produce.

```python
    if route.workflow_type == WorkflowType.AP:
        assessment = assess_accounts_payable(extraction, context)
        decision = decide_accounts_payable(extraction, context)
        workflow_result = WorkflowResult(
            workflow_type=route.workflow_type,
            extraction=extraction,
            ap_decision=decision,
        )
        assessment_payload = _serialize_ap_assessment(assessment)
    else:
        assessment = assess_accounts_receivable(extraction, context)
        decision = draft_accounts_receivable(extraction, context)
        workflow_result = WorkflowResult(
            workflow_type=route.workflow_type,
            extraction=extraction,
            ar_decision=decision,
        )
        assessment_payload = _serialize_ar_assessment(assessment)
```

Technical detail:
Once routing is done, the project branches into two separate decision systems.

- AP uses `decide_accounts_payable(...)`
- AR uses `draft_accounts_receivable(...)`

This keeps your project honest.
You are not pretending all finance cases are the same.

That is one of the biggest architectural wins in the repo.

---

### 2. The Extractor

File:

`app/agents/extractor.py`

This file turns messy finance text into structured fields.

That is one of the hardest and most important jobs in the whole pipeline.

#### Why This File Matters

If extraction is weak, everything later becomes weak too.

Routing depends on it.
Grounding depends on it.
Decision logic depends on it.

So the extractor is the bridge between messy real-world input and clean machine-friendly workflow logic.

#### Mode Selection

**app/agents/extractor.py:53-71**

Plain English:
The extractor can work in more than one mode. It can use heuristic parsing, or it can use an LLM path if configuration is available.

```python
    def extract(self, document: DocumentText) -> InvoiceExtraction:
        """Extract structured fields from a loaded document."""

        mode = self.mode.lower().strip()
        if mode not in {"auto", "heuristic", "llm"}:
            raise ExtractionError(f"Unsupported extractor mode: {self.mode}")

        if mode == "heuristic":
            self.last_mode_used = "heuristic"
            return self._extract_with_heuristics(document)
        if mode == "llm":
            self.last_mode_used = "llm"
            return self._extract_with_llm(document)

        if self._has_llm_configuration():
            self.last_mode_used = "llm"
            return self._extract_with_llm(document)
        self.last_mode_used = "heuristic"
        return self._extract_with_heuristics(document)
```

Technical detail:
This design gives the project flexibility.

- `heuristic` mode lets the project work offline with sample fixtures.
- `llm` mode lets the same interface work with prompt-based extraction.
- `auto` mode chooses intelligently based on environment.

This is a good engineering move because the project stays demoable even without live API keys.

#### Heuristic Extraction

**app/agents/extractor.py:83-106**

Plain English:
This block builds a clean extraction payload from the document text without needing a model.

```python
    def _extract_with_heuristics(self, document: DocumentText) -> InvoiceExtraction:
        fields = self._parse_key_value_fields(document.text)
        document_type = self._resolve_document_type(fields, document.text)
        warnings = list(document.warnings)

        payload = {
            "document_type": document_type.value,
            "vendor_name": fields.get("vendor_name"),
            "customer_name": fields.get("customer_name"),
            "invoice_number": fields.get("invoice_number"),
            "po_number": fields.get("po_number"),
            "amount": _parse_float(fields.get("amount")),
            "currency": _normalize_currency(fields.get("currency")),
            "issue_date": _parse_date_string(fields.get("issue_date"), warnings, "issue_date"),
            "due_date": _parse_date_string(fields.get("due_date"), warnings, "due_date"),
            "payment_terms": fields.get("payment_terms"),
            "line_items": self._parse_line_items(document.text) if document_type == DocumentType.INVOICE else [],
            "source_text_excerpt": self._make_excerpt(document.text),
            "missing_fields": [],
            "extraction_warnings": warnings,
        }
```

Technical detail:
This is deterministic parsing.

The extractor:

- reads key/value style text,
- determines the document type,
- parses floats and dates,
- pulls out line items,
- creates a source excerpt,
- and fills a schema-aligned payload.

This is important because it gives you a stable baseline to test the rest of the pipeline against.

#### Validation And Retry

**app/agents/extractor.py:245-285**

Plain English:
This block makes sure bad extraction output gets repaired instead of quietly flowing through the system.

```python
    def _validate_with_retry(
        self,
        document: DocumentText,
        payload: dict[str, Any],
        client: Any | None = None,
    ) -> InvoiceExtraction:
        working_payload = self._normalize_payload(document, payload)
        last_error: str | None = None

        for attempt in range(self.max_validation_retries + 1):
            try:
                return InvoiceExtraction.model_validate(working_payload)
            except ValidationError as exc:
                last_error = self._summarize_validation_error(exc)
                if attempt >= self.max_validation_retries:
                    raise ExtractionError(
                        f"Extraction failed schema validation after {attempt + 1} attempts: {last_error}"
                    ) from exc
```

Technical detail:
This is one of the more mature parts of the repo.

You did not trust raw output blindly.

Instead, you:

- normalize fields,
- validate with Pydantic,
- retry on failure,
- and use local or LLM-based repair paths.

That is exactly the kind of thing that makes a workflow system feel reliable instead of fragile.

---

### 3. Grounding And Retrieval

File:

`app/agents/research.py`

This file turns structured extraction data into a retrieval query and then packages the result into something the decision layers can use.

#### Why This File Matters

This is the difference between:

- "the model said so"

and

- "the system found the relevant policy section and used that as evidence."

That second version is much more believable in a finance workflow.

#### Building Grounded Context

**app/agents/research.py:58-85**

Plain English:
This function takes the extracted finance fields and the route, searches the knowledge base, and bundles the results into a reusable evidence package.

```python
def assemble_grounded_policy_context(
    extraction: ExtractionLike,
    route: WorkflowRouteLike,
    index: KnowledgeIndex,
    *,
    top_k: int = 5,
) -> GroundedPolicyContext:
    """Build the grounded retrieval context the decision layers will consume."""

    workflow_type = _normalize_workflow_type(route.workflow_type)
    query_text = build_policy_query(extraction, workflow_type)
    hits = query_knowledge_index(
        index,
        query_text,
        top_k=top_k,
        workflow_hint=_workflow_hint(workflow_type),
    )
    evidence_payloads = hits_to_evidence_payloads(hits)
```

Technical detail:
The extracted fields are not just stored.
They are turned into a retrieval query.

That means your knowledge lookup depends on actual document details like:

- vendor or customer,
- invoice number,
- amount,
- due date,
- payment terms,
- whether a PO exists,
- and which workflow branch is active.

This is a better design than dropping the entire document into one huge prompt.

#### Query Construction

**app/agents/research.py:88-121**

Plain English:
This code decides what information the retrieval system should care about when searching the knowledge base.

```python
def build_policy_query(extraction: ExtractionLike, workflow_type: str) -> str:
    """Create a retrieval-friendly policy query from structured extraction fields."""

    base_parts = [
        f"workflow {workflow_type}",
        f"document type {_string_value(extraction.document_type)}",
    ]

    if workflow_type == "accounts_payable":
        base_parts.extend(
            [
                f"vendor {_fallback_text(extraction.vendor_name, 'unknown')}",
                f"invoice {_fallback_text(extraction.invoice_number, 'unknown')}",
                f"amount {_fallback_number(extraction.amount)}",
                f"currency {_fallback_text(_string_value(extraction.currency), 'unknown')}",
                f"payment terms {_fallback_text(extraction.payment_terms, 'unknown')}",
                "purchase order present" if extraction.po_number else "purchase order missing",
            ]
        )
```

Technical detail:
This is retrieval by intent, not retrieval by raw noise.

You are telling the KB search:

- what type of workflow is happening,
- what fields matter,
- and what kind of signal should influence the search.

That is why your retrieval step is small but meaningful.

---

### 4. AP Decision Logic

File:

`app/agents/decision.py`

This file answers the AP question:

**What should happen to this invoice?**

#### Decision Resolution

**app/agents/decision.py:28-58**

Plain English:
This code looks at the detected AP issues and turns them into a finance action.

```python
def decide_accounts_payable(
    extraction: APExtractionLike,
    context: GroundedPolicyContext,
) -> APDecision:
    """Produce the AP recommendation, anomalies, and reviewer summary."""

    assessment = assess_accounts_payable(extraction, context)
    anomalies = assessment.anomalies
    recommendation = _resolve_ap_recommendation(anomalies)
    reviewer_summary = _build_reviewer_summary(recommendation, anomalies, extraction)
    confidence = _estimate_confidence(recommendation, anomalies, context, assessment)
    evidence = _select_evidence(context)
```

Technical detail:
The AP path does not output free-form text first.
It outputs a structured decision object.

That object contains:

- the recommendation,
- anomalies,
- a reviewer summary,
- evidence,
- and confidence.

This is exactly the right shape for workflow automation.

#### Rule Mapping

**app/agents/decision.py:50-58**

Plain English:
These rules explain how the system decides between approve, review, reject, and missing-info.

```python
def _resolve_ap_recommendation(anomalies: list[AnomalyFlag]) -> ApprovalRecommendation:
    codes = {anomaly.code for anomaly in anomalies}
    if "invalid_invoice" in codes:
        return ApprovalRecommendation.REJECT
    if "missing_required_fields" in codes or "missing_po" in codes:
        return ApprovalRecommendation.MISSING_INFO
    if "duplicate_invoice" in codes or "terms_mismatch" in codes or "approval_threshold" in codes:
        return ApprovalRecommendation.REVIEW
    return ApprovalRecommendation.APPROVE
```

Technical detail:
This is simple, clear, and maintainable.

You are not hiding the decision logic behind model magic.

That is good because finance workflow systems often need rule visibility.

If somebody asks why a decision was made, the answer can be traced.

---

### 5. AR Drafting Logic

File:

`app/agents/editor.py`

This file answers the AR question:

**What should we send back to the customer?**

#### Draft Generation

**app/agents/editor.py:28-58**

Plain English:
This is the AR version of the final business-action layer. It decides the escalation level and builds the actual follow-up output.

```python
def draft_accounts_receivable(
    extraction: ARExtractionLike,
    context: GroundedPolicyContext,
) -> ARDecision:
    """Produce the AR escalation level, subject, and follow-up draft."""

    assessment = assess_accounts_receivable(extraction, context)
    escalation_level = assessment.escalation_level
    payment_claim = assessment.payment_claim
    subject = _build_subject(extraction, assessment)
    draft = _build_followup_draft(
        extraction=extraction,
        assessment=assessment,
    )
```

Technical detail:
The AR path is built as a workflow outcome, not as a chat reply.

The output includes:

- escalation level,
- email subject,
- email body,
- TTS-safe subject,
- TTS-safe body,
- evidence,
- and confidence.

That means the project supports both normal written follow-up and a possible voice-based future path.

#### TTS-Safe Output

**app/agents/editor.py:134-203**

Plain English:
This section rewrites the follow-up message so invoice IDs, dates, and amounts can be read aloud more naturally by a voice system.

```python
def _build_subject_tts(
    extraction: ARExtractionLike,
    assessment: ARWorkflowAssessment,
) -> str:
    invoice_number_text = tts_safe_identifier(extraction.invoice_number, label="invoice")
    if assessment.payment_claim:
        return f"Follow-up on payment confirmation for {invoice_number_text}"
```

Technical detail:
This is a very practical addition.

Most demos stop at text.
You added a second output form optimized for speech.

That strengthens your story because it shows you thought about downstream use cases, not just the immediate JSON output.

---

### 6. Audit Trail

File:

`app/orchestrator/audit.py`

This file records what happened during a workflow run.

#### Why This File Matters

A lot of AI demos return an answer but tell you nothing about how they got there.

Your project records:

- which extractor mode was requested,
- which mode actually ran,
- which prompt version was involved,
- how long each stage took,
- which chunks were retrieved,
- and what final action was chosen.

That makes the system easier to inspect and debug.

#### Audit Structure

**app/orchestrator/audit.py:21-38**

Plain English:
This dataclass defines the full observability record for one workflow run.

```python
@dataclass(slots=True)
class WorkflowAuditTrail:
    generated_at_utc: str
    requested_extractor_mode: str
    effective_extractor_mode: str
    prompt_version: str
    prompt_path: str
    repair_prompt_version: str
    repair_prompt_path: str
    prompt_applied: bool
    stage_latencies_ms: dict[str, float]
    total_latency_ms: float
    route_reason: str
    matched_signals: list[str]
    retrieval_query: str
    final_recommendation: dict[str, Any]
    evidence_sources: list[dict[str, Any]]
    retrieved_chunks: list[dict[str, Any]]
```

Technical detail:
This is observability by design.

Instead of logging random strings, you created a clean audit payload that can be serialized and returned through the backend response.

That is a strong production-style pattern.

---

## How The Pieces Connect

Here is the story form of your app:

1. A sample or uploaded file enters the system.
2. The ingestion layer reads its contents.
3. The extractor turns that into a structured extraction object.
4. The router decides AP or AR.
5. The research layer builds a retrieval query from those fields.
6. The KB search returns relevant policy chunks.
7. The AP or AR path produces the final business action.
8. The audit layer records what happened.
9. The API returns all of this as JSON.
10. The UI displays the route, action, evidence, and metadata.

That story is the whole product.

```text
sample/upload
    -> ingestion
    -> extraction
    -> route
    -> grounded policy context
    -> AP recommendation or AR draft
    -> audit trail
    -> API response
    -> UI / eval / demo
```

---

## The Main Patterns You Used

### Pattern 1: Structured Schemas First

What it is for:
Make sure the system produces data in a shape the rest of the pipeline can trust.

Why it matters:
This prevents later stages from handling random or inconsistent output.

You used this idea in extraction and decision payloads.

### Pattern 2: Deterministic Routing Before Reasoning

What it is for:
Decide the workflow branch clearly before later business logic runs.

Why it matters:
AP and AR are different jobs.
You should not let them blur together.

### Pattern 3: Retrieval Before Final Action

What it is for:
Bring policy evidence into the workflow before the final recommendation or draft is created.

Why it matters:
This makes outputs more explainable and less random.

### Pattern 4: Fallback-Friendly Design

What it is for:
Let the project work even without live model APIs.

Why it matters:
It keeps the repo demoable, testable, and easier to develop.

### Pattern 5: Observability Built In

What it is for:
Record what happened during a run instead of treating the system like a black box.

Why it matters:
This helps debugging, demos, and future production thinking.

---

## What Makes This Better Than A Generic Chatbot

The project does not just answer questions.

It does five smarter things:

1. It expects specific workflow input.
2. It converts that input into structured data.
3. It looks up policy context.
4. It chooses a business action.
5. It returns evidence and metadata with the action.

That is why this repo is much more aligned with workflow automation roles.

---

## What The Sample Cases Are For

Your sample cases are not filler.

They are the controlled environment that makes the whole project understandable.

They let you demonstrate:

- missing PO cases,
- duplicate invoice cases,
- first reminder cases,
- payment-claim-without-proof cases.

That is how you make the pipeline feel real without needing private company data.

---

## Evaluation: Why It Matters

You added an evaluation layer because workflow systems should be measured.

The project checks things like:

- workflow match,
- extraction field match,
- anomaly coverage,
- citation coverage,
- subject coverage,
- draft mention coverage,
- latency.

That matters because a system can "look good" in a demo while still failing important workflow expectations.

Your eval layer helps expose those weak spots.

That is why you already know:

- routing is strong,
- anomaly detection is strong,
- extraction is mostly good,
- citation coverage still needs work,
- some AR phrasing still needs tightening.

That is honest engineering.

---

## Edge Cases And Gotchas

### 1. OCR Is Not Guaranteed

In plain English:
Some PDFs look readable to a human but are actually image-based, which makes text extraction harder.

Technical cause:
PDFs can contain selectable text or just embedded images.

How you handled it:
You built OCR fallback hooks instead of assuming all PDFs are text-friendly.

### 2. Missing Data Is Normal

In plain English:
Real finance documents are often incomplete.

Technical cause:
Fields like due date, PO number, or invoice number may be absent or ambiguous.

How you handled it:
You use `missing_fields`, warnings, and `missing_info` outcomes instead of pretending the data is clean.

### 3. Retrieval Can Still Miss The Best Policy Chunk

In plain English:
The system may find policy, but not always the exact best evidence chunk you hoped for.

Technical cause:
Small lexical retrieval is useful but not perfect.

How you handled it:
You added evaluation so citation gaps are visible rather than hidden.

### 4. Local Runtime Is Still Dependency-Sensitive

In plain English:
The code is built, but it still depends on packages like `pydantic` being installed in the environment.

Technical cause:
The backend and validation stack require the project dependencies to exist locally.

Why this matters:
A repo can be architecturally complete even when the active environment is not fully prepared.

### 5. Heuristic Mode Is Sample-Oriented

In plain English:
The current fallback extraction path is designed mainly for your synthetic fixtures, not arbitrary real-world documents.

Technical cause:
Heuristic parsing uses patterns and assumptions shaped around the sample dataset.

What this means:
The LLM path is more general, but the heuristic path is mainly there for development reliability.

---

## What You Should Say This Project Taught You

If somebody asks what you learned, a strong answer would be:

1. how to design a workflow pipeline instead of a one-shot AI script
2. how to use structured schemas to keep later stages clean
3. how to separate routing, grounding, and business logic
4. how to record evidence and observability metadata
5. how to evaluate a workflow system beyond "it kind of worked"

That is a much stronger story than just saying:

"I built an AI app."

---

## How This Connects To Bigger Concepts

- **RAG**: your retrieval layer is a compact, workflow-focused version of retrieval-augmented generation
- **Agentic systems**: your project has multiple stages with specialized roles, even if they are not branded as autonomous agents
- **Backend engineering**: FastAPI, data flow, serialization, and pipeline orchestration are all backend work
- **Workflow automation**: this is the real theme of the repo
- **Observability**: the audit trail is an early production-thinking signal

---

## What I Would Improve Next

If you continue this project later, these are the best next upgrades:

1. strengthen citation selection so the expected policy IDs show up more reliably
2. tighten AR subject/body phrasing to improve eval pass rate
3. connect OCR to a fully validated local Tesseract setup and test scanned-PDF cases end to end
4. add live deployment
5. widen the eval set beyond the seven current synthetic cases
6. possibly store audit trails for later inspection instead of only returning them in responses

---

## If You Want The Shortest Honest Summary

You built:

- a FastAPI backend,
- with structured extraction,
- AP/AR routing,
- policy retrieval,
- business-action outputs,
- evaluation,
- a simple UI,
- and an audit trail.

The product idea is:

**take finance documents in, and return grounded next steps out.**

That is what you made.

---

## Quick Reference

### The 8 Most Important Files

| File | What it does |
|------|---------------|
| `api/main.py` | exposes the backend routes |
| `app/orchestrator/engine.py` | runs the full workflow |
| `app/agents/extractor.py` | turns raw document text into structured data |
| `app/agents/research.py` | builds the grounded policy context |
| `app/agents/decision.py` | produces AP recommendations |
| `app/agents/editor.py` | produces AR follow-up drafts |
| `app/orchestrator/audit.py` | records prompt, latency, evidence, and final action |
| `app/eval/run_eval.py` | measures how well the system performs |

### The 2 Workflow Outputs

| Workflow | Output |
|----------|--------|
| AP | approve / review / reject / missing_info |
| AR | escalation level + follow-up draft |

### The 5 Stages To Remember

1. Ingest
2. Extract
3. Route
4. Ground
5. Decide / Draft

---

## Three Quiz Questions You Could Ask Yourself Later

1. Why is routing AP vs AR before the final logic an important design choice?
2. What is the difference between extraction and grounding in this project?
3. Why does the audit trail make this repo stronger than a simple demo app?

---

## Updates

- 2026-05-12 - Refined the operator UI so the top of the page is easier to understand instantly. The workflow summary now uses clearer top cards, the final recommendation is visually dominant, extracted key fields are surfaced directly, and the raw JSON is hidden inside a collapsible debug panel instead of taking over the main screen.
- 2026-05-14 - Verified the app in a separate clean virtual environment using the documented install steps. The backend started successfully, `/health` returned `ok`, and the AP sample workflow ran end to end against the clean setup.
- 2026-05-14 - Added screenshot-ready sample autorun support through `/ui?sample=...&mode=...&autorun=1`, captured real UI screenshots for the README, and generated a short local demo video asset from the live app.

---

*Generated: May 12, 2026 | Project: invoiceflow-ai | Key files: `app/orchestrator/engine.py`, `app/agents/extractor.py`, `app/agents/research.py`, `app/agents/decision.py`, `app/agents/editor.py`, `app/orchestrator/audit.py`*
