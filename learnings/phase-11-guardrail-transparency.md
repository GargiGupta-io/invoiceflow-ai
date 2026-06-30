# Phase 11: Prompt, Schema, And Guardrail Transparency

> This phase made the advanced AI workflow controls visible without forcing normal finance operators to read technical debug output.

---

## In Plain English

InvoiceFlow already showed the main finance answer: approve, review, missing info, reject, escalate, or draft a follow-up. That is what a finance operator needs first. But a technical reviewer also needs to know whether the system is controlled properly. They want to see which prompt version was used, whether the output followed a schema, whether retrieval repair happened, whether PII redaction was applied, and whether the system used a live LLM call or deterministic demo mode.

The main design challenge was not just “show more data.” Showing everything at once would make the page feel confusing again. The better approach was to keep the normal product flow clean and put the technical controls inside the collapsed Advanced Debug area. That way, a beginner can ignore it, while an engineer can inspect it.

This phase makes the project look more serious because it shows that the AI workflow is not treated as magic. It exposes the safety rails and operational metadata around the AI path.

## What Is Guardrail Transparency?

Guardrail transparency means showing the controls around an AI workflow. It answers questions like:

- Which prompt version was used?
- Was the extraction schema checked?
- Did the app use a live LLM or deterministic fallback?
- Was retrieval repair attempted?
- Were emails or phone numbers redacted before a model call?
- How many gateway calls happened?
- How long did each stage take?
- Are token/cost values available?

In a finance workflow, these details matter because the output can affect payment, escalation, or customer communication. A system that only says “AI decided this” is weak. A system that says “here is the recommendation, here is the evidence, and here are the controls behind the run” is much more trustworthy.

## The Problem It Solves

Before this phase, InvoiceFlow had raw JSON and some audit metadata, but the technical story was still hard to read. An engineer could inspect the full payload, but they had to know what to look for.

That creates a problem in a portfolio project. If a reviewer has only a few minutes, they may miss the guardrail work entirely. The project could have strong internals but still look like a simple prompt wrapper.

The new guardrail panel solves that by summarizing the important technical metadata in one collapsed place:

```text
Advanced Debug
  -> Prompt version
  -> Extractor mode
  -> Schema validation
  -> Repair attempted
  -> PII redaction
  -> LLM gateway calls
  -> Latency by stage
  -> Token / cost metadata
```

## What We Built

### Collapsed Technical Panel

Plain English: The technical details are available, but hidden until someone asks for them.

File changed:

```text
web/index.html
```

The panel lives inside the existing `Advanced Debug` disclosure. That is important because the main screen remains focused on the finance decision.

The panel starts with placeholder cards:

```text
Prompt version
Schema validation
LLM gateway
```

After a workflow runs, JavaScript replaces those placeholders with real audit metadata.

### Guardrail Renderer

Plain English: The frontend reads the backend audit trail and turns it into human-readable cards.

File changed:

```text
web/app.js
```

The renderer uses the existing workflow payload:

```text
payload.audit_trail
payload.workflow_result.extraction
```

It does not invent new backend data. It organizes fields that already exist:

```text
audit.prompt_version
audit.effective_extractor_mode
audit.requested_extractor_mode
audit.prompt_applied
audit.retrieval_repair
audit.llm_gateway
audit.stage_latencies_ms
audit.total_latency_ms
extraction.extraction_warnings
extraction.missing_fields
```

This means the UI improvement is low-risk. It changes presentation, not the workflow engine.

### Technical Grid Styling

Plain English: The advanced cards look compact and calm instead of becoming another large dashboard.

File changed:

```text
web/styles.css
```

The styling uses the existing InvoiceFlow color system:

- copper labels
- muted explanatory text
- subtle borders
- light card backgrounds
- responsive stacking on mobile

The cards are designed to feel like a technical readout, not a marketing block.

## How It Works

### Data Flow

Plain English: The backend sends one audit object, and the frontend picks the important parts to show.

```text
Run sample or upload
        |
        v
FastAPI workflow endpoint
        |
        v
workflow result + audit_trail
        |
        v
renderResult(payload)
        |
        v
renderGuardrailPanel(audit, extraction)
        |
        v
Advanced Debug cards update
```

The key point is that the same payload powers both the raw JSON and the readable guardrail cards. Raw JSON remains available for deep inspection, but the cards give a fast summary.

### Prompt Version

Plain English: The app shows which extractor prompt version belongs to the run.

The backend already returns:

```text
prompt_version: extractor_v1
repair_prompt_version: extractor_repair_v1
```

The panel shows those as readable labels. This matters because prompt versions let technical reviewers understand whether prompt changes are tracked.

### Extractor Mode

Plain English: The app explains whether it used live LLM extraction or deterministic fallback.

The backend returns:

```text
requested_extractor_mode
effective_extractor_mode
prompt_applied
```

For demo mode, the effective mode is often `heuristic`, and `prompt_applied` is false. That is not a weakness. It means the demo can work without paid API keys while still showing where live LLM mode would be inspected.

### Schema Validation

Plain English: The app shows whether the backend returned a structured extraction object.

The panel uses:

```text
extraction.missing_fields
extraction.extraction_warnings
```

If there are missing fields, the panel says the schema passed with missing fields. That distinction matters. Missing business information is not the same as a broken payload. A finance workflow can still produce a safe `missing_info` recommendation.

### Repair Attempted

Plain English: The app shows whether retrieval had to repair weak or missing evidence.

The panel uses:

```text
audit.retrieval_repair.attempted
audit.retrieval_repair.success
audit.retrieval_repair.reason
```

This is important because self-healing retrieval is easy to claim and hard to notice. The card makes it visible.

### PII Redaction

Plain English: If a live gateway call happens, the app can show whether emails or phone numbers were redacted.

The panel reads:

```text
audit.llm_gateway[].redaction_counts
```

In deterministic demo mode, there are no live calls, so it says `No live call`. That is honest and useful. It avoids pretending there was a model call when there was not.

### LLM Gateway Calls

Plain English: The app shows whether a model gateway was actually used.

The panel counts:

```text
audit.llm_gateway.length
```

When live LLM mode is configured, this can also show model and response-format metadata.

### Latency By Stage

Plain English: The app shows where time was spent.

The panel uses:

```text
audit.stage_latencies_ms
audit.total_latency_ms
```

Example stages include:

```text
knowledge_index
ingestion
extraction
routing
grounding
decision
```

This helps technical reviewers see that the workflow is instrumented, not just returning a final answer.

### Token / Cost Metadata

Plain English: Token information appears when a live provider returns it.

In demo mode, token and cost metadata may not exist. The UI says this clearly:

```text
Demo mode avoids paid gateway usage, so cost metadata is intentionally absent.
```

That is better than showing zero as if zero tokens were used in a real model call.

## Why This Improves InvoiceFlow

This phase improves the project in four ways.

First, it makes the technical story visible. A reviewer can see prompt/schema/guardrail thinking without reading backend files.

Second, it protects the beginner experience. The guardrail panel is collapsed under Advanced Debug, so the main page remains decision-first.

Third, it is honest about demo mode. It clearly distinguishes deterministic fallback from live gateway usage.

Fourth, it strengthens the claim that InvoiceFlow is more than a generic chatbot. The app shows structured extraction, retrieval repair, audit metadata, and gateway observability in the product surface.

## Design Tradeoffs

### Why Not Put This On The Main Result Page?

Plain English: Most finance operators do not need to see prompt and token metadata before making sense of the recommendation.

The main page should answer:

```text
What should I do?
Why?
How risky is it?
Does a person need to review it?
What evidence supports it?
```

Prompt versions and gateway metadata are useful, but secondary.

### Why Not Show The Full Prompt?

Plain English: Showing prompt version is safer than exposing full prompt text in the frontend.

The app should not leak sensitive internal prompt details or secrets. A version label gives technical reviewers evidence that prompts are tracked without exposing everything.

### Why Use Existing Audit Fields?

Plain English: It is safer to display data that already exists than to change backend contracts just for UI polish.

The backend already had a strong audit payload. This phase turned it into a readable frontend panel without rewriting the workflow.

## Edge Cases And Gotchas

### Deterministic Demo Mode

In plain English: The app may show zero gateway calls because it did not use a live LLM.

Technical cause: Demo mode can run with heuristic extraction so the project works without API keys.

How to handle: Say `No live call` and explain that live mode records gateway metadata when configured.

### Missing Token Metadata

In plain English: Token count may be unavailable even when the workflow is valid.

Technical cause: Token metadata depends on whether the provider returns usage fields and whether a live gateway was used.

How to handle: Show `Not available` instead of inventing cost values.

### Missing Business Fields

In plain English: An invoice missing a PO can still have a valid extraction object.

Technical cause: Schema validation checks structure. Business validation checks whether required finance facts are present.

How to handle: Distinguish `Passed with missing fields` from a broken schema.

### Too Much Debug Data

In plain English: Technical proof can overwhelm the product if shown too early.

Technical cause: Audit metadata is dense and not part of the finance operator’s first decision.

How to handle: Keep it collapsed under Advanced Debug.

## How It Connects To Other Concepts

- **Evidence panel**: Shows why the decision is grounded in policy.
- **Audit trail**: Shows what the workflow did.
- **Guardrail panel**: Shows how the AI path was controlled.
- **Evaluation dashboard**: Shows whether the workflow behaves correctly across cases.
- **Demo mode**: Lets the app work without paid keys while still exposing where live metadata would appear.
- **Human review gate**: Turns uncertainty into a safe operator workflow.

## Quick Reference

### Files Changed In This Phase

```text
web/index.html
web/app.js
web/styles.css
steps.md
```

### Main Function Added

```text
renderGuardrailPanel(container, audit, extraction)
```

### Data Sources Used

```text
audit.prompt_version
audit.repair_prompt_version
audit.requested_extractor_mode
audit.effective_extractor_mode
audit.prompt_applied
audit.retrieval_repair
audit.llm_gateway
audit.stage_latencies_ms
audit.total_latency_ms
extraction.missing_fields
extraction.extraction_warnings
```

### What A Technical Reviewer Can Now Inspect

```text
Prompt version
Extractor mode
Schema validation
Repair attempted
PII redaction
LLM gateway calls
Latency by stage
Token / cost metadata
Raw JSON
```

## Quiz Questions

1. Why should prompt/schema metadata live under Advanced Debug instead of the main decision card?
2. What is the difference between schema validation and missing business information?
3. Why is it important to show when no live LLM gateway call happened?
4. How does retrieval repair metadata support the self-healing RAG story?
5. Why is prompt version safer to expose than full prompt text?

---

*Generated: 2026-06-30 | Project: invoiceflow-ai | Files: web/index.html, web/app.js, web/styles.css, steps.md*
