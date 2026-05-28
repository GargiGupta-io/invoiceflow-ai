# Workflow Trace View

> A workflow trace is the visible checklist that explains how InvoiceFlow AI moved from raw document data to a finance recommendation.

---

## In Plain English

The trace view is like a receipt for the decision. Instead of only showing "Review" or "Missing Info," the interface now shows the four checkpoints that happened before the recommendation: what the system read, what policy it found, what checks it ran, and what action it recommends.

This matters because finance work needs trust. If an invoice is blocked, a reviewer should not have to guess whether the reason came from a missing field, a policy rule, a duplicate hint, or a weak source. The trace makes that path visible without forcing the user to open raw JSON.

The result is a product that feels more like an operations console and less like a black-box AI demo. A recruiter or reviewer can run a sample and immediately see the logic trail.

## What Is A Workflow Trace?

A workflow trace is a short, ordered explanation of the system's major stages. It does not replace detailed logs or raw JSON. It summarizes them into a format that a human operator can scan.

In this project, the trace has four stages:

1. Extraction
2. Retrieval
3. Validation
4. Decision

That sequence mirrors the product story:

```text
Document or email
      |
      v
Extract structured fields
      |
      v
Retrieve policy evidence
      |
      v
Validate against checks and review gates
      |
      v
Return operator action
```

## The Problem It Solves

Before this step, the UI already had better evidence cards and audit metadata, but the user still had to connect the pieces mentally. Extracted fields were in one column, evidence was in another column, and the final recommendation was above them.

That is fine for engineers, but a finance operator needs the flow:

```text
What did it read?
What policy did it use?
What check made this risky?
What should I do now?
```

The trace view answers those questions in order.

## How It Works

### Stage 1: Extraction

Plain English: this stage says whether the system captured the important invoice or email fields.

The UI reads `workflow.extraction` from the backend response. It checks fields such as document type, vendor/customer, invoice number, and `missing_fields`.

If there are missing fields, the trace says `Needs field review`. If not, it says `Schema captured`.

### Stage 2: Retrieval

Plain English: this stage says whether the system found policy evidence.

The UI reads the evidence list from the final AP or AR decision. It displays the number of evidence sources and names the top matched policy source.

It also includes RAG repair state from `audit.retrieval_repair`, which matters because weak or failed retrieval should not look as strong as a direct policy match.

### Stage 3: Validation

Plain English: this stage says whether the workflow found a reason for human review.

The UI reads `audit.human_review`. If review is required, the trace calls that out and shows the reason codes. If no review gate fired, it says the checks passed.

This makes the human review gate visible as a first-class product feature.

### Stage 4: Decision

Plain English: this stage says what the operator should do next.

For AP workflows, it shows the formatted recommendation, such as `Approve`, `Review`, or `Missing Info`.

For AR workflows, it shows whether the system produced a follow-up draft or an escalation recommendation.

## What We Built

### Overview

The result page now has a four-card flow strip above the inspection console columns. It uses the same backend payload already used by the result summary, so it does not create a second source of truth.

The trace is intentionally short. It is not meant to show every field or every tool call. It is meant to orient the reviewer before they inspect details.

### Markup

Plain English: the page now has four empty trace cards that wait for a workflow run.

**web/index.html**

```html
<div class="flow-map" aria-label="Workflow trace">
  <article class="flow-step">
    <span class="flow-index">01</span>
    <h3>Extraction</h3>
    <strong id="flow-extraction-status">Waiting</strong>
    <p id="flow-extraction-detail">Run a workflow to see parsed fields.</p>
  </article>
  ...
</div>
```

Technical detail: each card has stable IDs for the status and detail text. JavaScript updates only the text content, which keeps the layout stable and avoids rebuilding the section after every run.

### JavaScript Flow Update

Plain English: after a workflow finishes, the app fills each trace card with the right summary.

**web/app.js**

```js
updateFlowMap(extraction, evidence, audit, finalDecision, workflow.workflow_type);
```

Technical detail: `renderResult` already computes `extraction`, `evidence`, `audit`, and `finalDecision`. Passing those values into one dedicated trace function keeps the trace logic separate from the larger result rendering block.

### Trace Builder

Plain English: this helper turns raw response details into readable operator language.

**web/app.js**

```js
function updateFlowMap(extraction, evidence, audit, finalDecision, workflowType) {
  const review = audit.human_review || {};
  const missingFields = Array.isArray(extraction.missing_fields) ? extraction.missing_fields : [];
  const repair = audit.retrieval_repair || {};

  flowExtractionStatus.textContent = missingFields.length ? "Needs field review" : "Schema captured";
  flowExtractionDetail.textContent = buildExtractionFlowDetail(extraction, workflowType, missingFields);

  flowRetrievalStatus.textContent = evidence.length === 1 ? "1 source" : `${evidence.length} sources`;
  flowRetrievalDetail.textContent = buildRetrievalFlowDetail(evidence, repair);

  flowValidationStatus.textContent = review.required ? "Review gate" : "Checks passed";
  flowValidationDetail.textContent = review.required
    ? `${review.blocking ? "Blocking" : "Non-blocking"}: ${(review.reason_codes || []).join(", ") || "policy review"}`
    : "No blocking validation issue was returned.";

  flowDecisionStatus.textContent = buildDecisionFlowStatus(finalDecision, workflowType);
  flowDecisionDetail.textContent = buildDecisionFlowDetail(finalDecision, workflowType);
}
```

Technical detail: the function avoids assuming the backend always returns perfect data. It defaults missing nested objects to `{}` and missing arrays to `[]`, which keeps the UI from crashing on partial responses.

### Styling

Plain English: the trace looks like a compact process strip on desktop and stacks cleanly on smaller screens.

**web/styles.css**

```css
.flow-map {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin: 0 0 18px;
}
```

Technical detail: `minmax(0, 1fr)` prevents long text from forcing grid columns wider than the container. The detail text uses `overflow-wrap: anywhere` so invoice IDs, policy IDs, or unusual strings do not break the layout.

## How The Pieces Connect

Plain English: the trace is a bridge between the top decision card and the deeper inspection console.

```text
Backend sample/upload response
      |
      v
renderResult(payload)
      |
      +--> top decision summary
      +--> workflow trace view
      +--> extracted fields
      +--> evidence cards
      +--> agent tool trace
      +--> audit metadata
      +--> raw JSON debug drawer
```

The trace does not compete with the detail columns. It gives the reviewer a quick map first, then the columns provide evidence and debugging depth.

## Common Patterns

### Pattern 1: Decision-First UI

What it is for: show the human action before showing debugging detail.

The workflow trace supports this by staying close to the final recommendation. It helps a user understand the decision path without scrolling into raw JSON.

### Pattern 2: Derived UI State

What it is for: avoid duplicating backend data just to display a new panel.

The trace derives its labels from existing fields:

```text
extraction.missing_fields -> Extraction status
decision.evidence -> Retrieval status
audit.human_review -> Validation status
ap_decision / ar_decision -> Decision status
```

### Pattern 3: Safe Defaults

What it is for: keep the interface useful even when part of a response is missing.

The trace helpers default to readable fallbacks such as `policy source`, `confidence pending`, and `reviewer summary pending`.

## Edge Cases And Gotchas

1. **No evidence returned**
   Plain English: the trace must not pretend the system found support when it did not.
   Technical cause: the evidence array can be empty.
   How to avoid: show "No supporting policy evidence was returned" and rely on review gates for weak evidence.

2. **Partial extraction**
   Plain English: missing invoice fields should be obvious.
   Technical cause: `missing_fields` may include required AP or AR fields.
   How to avoid: label the extraction stage as `Needs field review`.

3. **AP and AR decisions differ**
   Plain English: invoice approval and receivables follow-up have different final actions.
   Technical cause: AP uses `recommendation`; AR uses `escalation_level` and email draft fields.
   How to avoid: branch by `workflowType` in the decision helper.

4. **Long text in a compact card**
   Plain English: policy titles and reviewer summaries can be long.
   Technical cause: grid cards can overflow if text is not wrapped.
   How to avoid: use stable grid columns and `overflow-wrap`.

## How It Connects To Other Concepts

- **RAG transparency**: the retrieval stage turns policy matching into something visible.
- **Human review gates**: the validation stage makes review reasons clear before the user reads audit metadata.
- **Structured extraction**: the extraction stage shows whether the schema has enough data to trust the workflow.
- **Evaluation mindset**: a trace is useful for debugging failed cases because it shows which stage produced weak output.

## Going Deeper

### Self-Healing RAG

Plain English: if the first retrieval attempt is weak, the system can try to repair the search.

The trace already exposes `retrieval_repair`, which can later become a stronger self-healing RAG story with retry strategy, query rewrite details, and confidence scoring.

### Guardrail Gateway

Plain English: a gateway checks whether model output is safe and valid before the app trusts it.

The validation stage is where schema status, redaction status, and policy conflicts can become visible later.

### Eval CI

Plain English: tests can fail the build if extraction, citations, or review gates regress.

The trace gives a UI shape that matches what evals should measure: extraction, retrieval, validation, and decision quality.

## Quick Reference

### Key Terms

| Term | Plain English meaning | Technical meaning |
|------|-----------------------|-------------------|
| Extraction | What the system read from the invoice or email | `workflow.extraction` |
| Retrieval | What policy/context the system found | `finalDecision.evidence` |
| Validation | What checks or review gates fired | `audit.human_review` |
| Decision | What the operator should do | `ap_decision.recommendation` or `ar_decision.escalation_level` |
| RAG repair | A retry when retrieval is weak | `audit.retrieval_repair` |

### Essential Flow

```js
const extraction = workflow.extraction || {};
const finalDecision = apDecision || arDecision || {};
const evidence = finalDecision.evidence || [];

updateFlowMap(extraction, evidence, audit, finalDecision, workflow.workflow_type);
```

---

*Generated: 2026-05-28 | Project: invoiceflow-ai | Files: web/index.html, web/app.js, web/styles.css*
