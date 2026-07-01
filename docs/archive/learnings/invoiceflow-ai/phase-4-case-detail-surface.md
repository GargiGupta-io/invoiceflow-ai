# Phase 4: Case Detail Surface

> Phase 4 turned the result area into the core product surface: decision first, evidence second, debug last.

---

## In Plain English

Before this phase, the app had useful finance workflow information, but the result page still made the user work too hard. A normal finance operator does not want to start with raw technical output. They want to know what to do, why the system recommends it, whether a person needs to review it, and what evidence supports the answer.

Phase 4 reorganized the screen around that natural order. The page now reads more like a finance review desk: first the recommendation, then confidence and risk, then supporting evidence, then review and audit details. Technical JSON is still available, but it is hidden behind an Advanced Debug disclosure so it does not distract non-technical users.

This matters because InvoiceFlow AI is supposed to feel like a paid-ready AI operations product, not a collection of AI outputs. A strong product surface should guide a user through the decision without requiring them to understand the backend first.

## What Is A Case Detail Surface?

A case detail surface is the main screen where one finance case gets reviewed. In this project, a case can be an Accounts Payable invoice or an Accounts Receivable follow-up. The surface needs to answer a few questions quickly:

- What is this case?
- What action is recommended?
- Why is that action recommended?
- What evidence supports it?
- Does a human need to review it?
- What happened in the audit trail?
- Where can an engineer inspect the raw response?

Technically, this is mostly frontend information architecture. The backend already returns extracted fields, evidence, recommendations, human review metadata, audit metadata, and raw JSON. Phase 4 did not rewrite that system. It changed how those pieces are presented so the most important information appears first.

## The Problem It Solves

The earlier UI had correct ingredients but weaker ordering. A viewer could see workflow, inspection, queue, evaluation, debug, JSON, and audit concepts all near each other. That is useful for a developer, but confusing for a beginner or recruiter who is trying to understand the product story.

The product needed a hierarchy:

```text
Operator question:
What should I do with this invoice or AR case?

Primary answer:
Recommendation + reason + confidence/risk + human review gate

Supporting answer:
Extracted fields + anomalies + policy evidence + tool trace

Technical answer:
Audit metadata + raw JSON hidden under Advanced Debug
```

That hierarchy makes the AI workflow feel safer because the system is not saying "trust me." It is saying "here is the recommended action, here is the reason, here is the evidence, and here is the audit trail."

## What We Built

Phase 4 had three steps.

### Step 11: Four Main Visible Areas

Plain English: The workspace labels were rewritten so the page feels organized around what a user actually needs after running a case.

The visible areas became:

1. Case Summary
2. Evidence & Reasoning
3. Human Review & Audit
4. Evaluation

This changed the navigation from technical or generic labels into product labels. "Evidence & Reasoning" is easier to understand than a generic inspection area. "Human Review & Audit" is clearer than a queue-only label because it describes the safety workflow.

### Step 12: Decision Comes First

Plain English: The top result card now starts with the operator action instead of metadata.

The key labels changed to user-first questions:

```html
<span class="result-label">What should the operator do?</span>
<strong id="decision-value">-</strong>
<p id="decision-summary">Run a case to see the recommended action and reason.</p>
```

Technical detail: The HTML still uses the same `decision-value` and `decision-summary` IDs, so the existing JavaScript rendering code continues to work. This is important because the redesign improved clarity without forcing a backend or rendering rewrite.

The JavaScript now makes the summary more explicit:

```javascript
decisionSummary.textContent = apDecision.reviewer_summary
  ? `Reason: ${apDecision.reviewer_summary}`
  : "Reason: no reviewer summary was returned.";
```

For AR cases, the result summary now frames the output as a draft subject:

```javascript
const arSubject = arDecision.subject || arDecision.followup_subject;
decisionSummary.textContent = arSubject
  ? `Draft subject: ${arSubject}`
  : "Draft subject: no subject generated.";
```

This makes AP and AR output easier to scan. AP is about a review decision. AR is about a follow-up draft or escalation.

### Step 13: Raw JSON Moves Behind Advanced Debug

Plain English: The app still exposes the raw backend payload, but it no longer looks like part of the normal finance workflow.

The old debug section looked like a full panel:

```html
<section class="panel raw-panel" data-tab-panel="inspect" hidden>
  ...
  <h2>Raw backend response</h2>
```

The new version is a compact advanced disclosure:

```html
<section class="advanced-debug-panel" data-tab-panel="inspect" hidden aria-label="Advanced debug">
  <details class="debug-disclosure">
    <summary>
      <span>Advanced Debug</span>
      <small>Raw JSON for technical review</small>
    </summary>
```

Technical detail: The `details` element keeps the raw JSON collapsed by default without needing extra JavaScript. The frontend still writes the raw response into `#raw-json`, but the user only sees it after intentionally opening the debug section.

## How The Pieces Connect

The frontend flow after Phase 4 looks like this:

```text
User runs sample or upload
        |
        v
Backend returns workflow payload
        |
        v
renderResult(payload)
        |
        +--> Case Summary: recommendation, reason, confidence, review gate
        |
        +--> Evidence & Reasoning: fields, anomalies, policy evidence, trace
        |
        +--> Human Review & Audit: risky cases and review queue
        |
        +--> Advanced Debug: raw JSON, collapsed by default
```

The important design decision is that every deeper layer still exists, but each layer is lower priority than the one before it. That is progressive disclosure.

## Common Patterns

### Pattern 1: Decision-First UI

What it is for: Put the action a user needs to take before the explanation details.

In InvoiceFlow AI, the operator first sees:

- recommendation
- reason
- confidence/risk
- human review required
- evidence count

Only after that do they inspect fields, evidence, trace, audit metadata, and raw JSON.

### Pattern 2: Progressive Disclosure

What it is for: Hide advanced details until the user asks for them.

This appears in the Advanced Debug panel. The raw JSON is valuable for engineers, but it is noise for a finance manager. Keeping it collapsed lets the same page serve both audiences.

### Pattern 3: Same Data, Better Framing

What it is for: Improve product clarity without rewriting working backend systems.

Phase 4 mostly reused existing IDs and payload fields:

- `decision-value`
- `decision-summary`
- `confidence-value`
- `review-value`
- `decision-evidence-value`
- `raw-json`

The app became clearer because the labels, order, and wording changed.

## Edge Cases & Gotchas

### 1. Debug data is useful, but it can make the product look unfinished

In plain English: If a user sees raw JSON too early, the app feels like a developer tool instead of a product.

Technical cause: The backend payload is complete and detailed, but raw JSON does not explain priority or meaning.

How to avoid: Keep raw payloads under collapsed debug panels and lead with human-readable summaries.

### 2. AP and AR need different summary language

In plain English: Invoice review and customer follow-up are not the same task.

Technical cause: AP results usually produce a recommendation like `approve`, `review`, or `missing_info`. AR results often produce an escalation level and an email draft.

How to avoid: Render AP summaries as reasons and AR summaries as draft subjects or escalation explanations.

### 3. Labels matter as much as layout

In plain English: A section called "Inspect" may make sense to a developer, but "Evidence & Reasoning" tells a beginner what they are looking at.

Technical cause: UI labels create the mental model before the user reads the contents.

How to avoid: Use labels that describe the user's goal, not the internal implementation.

## How It Connects To Other Concepts

- **RAG transparency**: Evidence needs to be visible near the recommendation, not buried in JSON.
- **Human-in-the-loop AI**: Review gates make risky outputs feel controlled instead of automatic.
- **Auditability**: Audit metadata stays available, but it supports the decision instead of leading the page.
- **Evaluation readiness**: A clean case detail surface makes it easier to show whether the workflow did the right thing.
- **Product positioning**: The UI now supports the story that InvoiceFlow AI is an operations console, not a generic AI demo.

## Quick Reference

### Files Changed In Phase 4

- `web/index.html`
  - Renamed workspace navigation and section headings.
  - Reworded the top decision card around operator questions.
  - Converted raw JSON into an Advanced Debug disclosure.

- `web/app.js`
  - Made AP decision summaries start with `Reason:`.
  - Made AR decision summaries start with `Draft subject:`.

- `web/styles.css`
  - Increased visual hierarchy for the decision recommendation.
  - Added quieter advanced debug styling.

- `steps.md`
  - Logged Steps 11, 12, and 13.

### Phase 4 Commits

- `e3de0dc copy: name four case areas`
- `9236414 docs: log four area case step`
- `80c063c copy: put operator decision first`
- `8239d29 docs: log decision first step`
- `6cf90a8 hide raw json behind debug`
- `7d1c449 docs: log debug disclosure step`

### Beginner Test

Can a beginner human understand this page as it goes?

Mostly yes after Phase 4. The page now starts with the decision, reason, confidence/risk, human review gate, and evidence count before asking the user to inspect deeper details. The remaining confusion will likely come from the Evidence & Reasoning tab still containing several advanced concepts at once, which future phases should simplify further with better explainability and evidence wording.

## Updates

- 2026-06-30 - Created after Phase 4 to document the case detail structure, decision-first summary, and Advanced Debug disclosure.
