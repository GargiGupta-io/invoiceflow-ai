# Human Review Queue

> A human review queue turns workflow output into an operator list that says what needs attention, why it was flagged, and what status it should have.

---

## In Plain English

The human review queue is the part of InvoiceFlow AI that turns a stream of AP and AR cases into a working inbox for finance ops. Instead of making the user hunt through sample outputs one by one, it gathers the cases that matter, labels them by risk, and shows why they need attention.

That matters because finance work is not just about getting an answer. It is about deciding whether the answer is safe enough to act on. A missing purchase order, a duplicate invoice hint, or a payment-claimed-without-proof email should not be buried inside raw JSON. The queue makes those cases visible in a way an operator can scan quickly.

This step also makes the product feel more like a real console. A recruiter or reviewer can see that the app does not stop at extraction and recommendation. It also gives a place for human review, which is the part that keeps risky automation honest.

## What Is A Human Review Queue?

A human review queue is a filtered list of work items that should be checked by a person before they are approved, rejected, or returned for more information. In a finance system, it is the handoff point between machine reasoning and human judgment.

In this project, the queue is built from the bundled AP and AR samples. Each sample runs through the workflow, produces a decision, and then gets translated into a queue row with:

- case id
- workflow type
- recommendation
- risk level
- reason for review
- timestamp
- status

That is enough for an operator to understand what happened without opening the whole workflow trace first.

## The Problem It Solves

Before a queue like this exists, the app can still make recommendations, but the operator has no single place to see what needs review. That leads to scattered checks: one result view for one sample, another state for another sample, and no clear priority order.

The queue solves that by giving the product a central review surface. It answers:

1. What cases need a person?
2. Why were they flagged?
3. How risky are they?
4. What status should the operator assign?

That is a better fit for finance than a generic "all results are equal" view. It also makes the system easier to demo because the user can see one queue change as they run samples.

## How It Works

The queue is built in layers.

1. The backend runs every bundled sample through the workflow.
2. The backend converts each workflow result into a queue item.
3. The API serves the queue as JSON.
4. The frontend fetches the queue on load and on refresh.
5. The table shows risk, reason, and status in a scan-friendly layout.

```text
sample fixtures
      |
      v
workflow runner
      |
      v
review queue builder
      |
      v
/review-queue JSON
      |
      v
operator table
```

### Backend Queue Builder

Plain English: this is the part that turns finished workflow cases into queue rows a human can read.

Technical detail: `app/orchestrator/engine.py:52-75` iterates through `list_sample_documents()`, runs each sample through `run_workflow_from_sample()`, and stores the converted rows in a payload with a timestamp and extractor mode.

```python
def build_review_queue(*, extractor_mode: str = "heuristic") -> dict[str, Any]:
    items = []
    for sample in list_sample_documents():
        workflow_payload = run_workflow_from_sample(
            sample["sample_id"],
            extractor_mode=extractor_mode,
        )
        items.append(_review_queue_item(sample["sample_id"], workflow_payload))

    return {
        "generated_at_utc": _utc_now(),
        "extractor_mode": extractor_mode,
        "item_count": len(items),
        "items": items,
    }
```

This function is the backbone of the queue. It is intentionally simple: it does not invent new cases, it just repackages the project’s actual bundled samples into a review list.

### Queue Item Mapping

Plain English: this is where a workflow result gets translated into something like "Needs Review" or "Approved."

Technical detail: `app/orchestrator/engine.py:261-335` looks at the workflow type, decision, and human review flags. It maps them into status, risk, and a short reason string.

```python
def _review_queue_item(sample_id: str, workflow_payload: dict[str, Any]) -> dict[str, Any]:
    audit = workflow_payload.get("audit", {})
    workflow_type = workflow_payload.get("workflow_type", "unknown")
    decision = workflow_payload.get("decision", {})
    human_review = workflow_payload.get("human_review", {})

    status = _review_queue_status(workflow_type, decision, human_review)
    risk_level = _review_queue_risk_level(human_review)

    return {
        "case_id": sample_id,
        "workflow_type": workflow_type,
        "recommendation": decision.get("decision", "review"),
        "risk_level": risk_level,
        "reason_for_review": _review_queue_reason(human_review, decision, workflow_type),
        "timestamp_utc": audit.get("generated_at_utc") or _utc_now(),
        "status": status,
    }
```

The important idea is that the queue does not just show the outcome. It explains the outcome in a compact form and keeps the timestamp tied to the original workflow audit when possible.

### Status And Risk Rules

Plain English: these helper functions decide whether something is approved, needs review, or should be returned for more information.

Technical detail: `_review_queue_status()` uses the workflow type and decision to choose a human-friendly status. `_review_queue_risk_level()` turns the review gate into a risk label. `_review_queue_reason()` turns the review flags into a short reason list.

```python
def _review_queue_status(
    workflow_type: str,
    decision: dict[str, Any],
    human_review: dict[str, Any],
) -> str:
    if workflow_type == "accounts_receivable":
        if human_review.get("blocking_review"):
            return "Escalated"
        if human_review.get("required"):
            return "Needs Review"
        return "Approved"

    decision_kind = decision.get("decision", "review")
    if decision_kind == "approve":
        return "Approved"
    if decision_kind == "missing_info":
        return "Returned for Info"
    if decision_kind == "reject":
        return "Rejected"
    if human_review.get("blocking_review"):
        return "Escalated"
    return "Needs Review"
```

```python
def _review_queue_risk_level(human_review: dict[str, Any]) -> str:
    if human_review.get("blocking_review"):
        return "High risk"
    if human_review.get("required"):
        return "Medium risk"
    return "Low risk"
```

These rules are deliberately opinionated. They make the queue feel like an operational tool instead of a loose list of outputs.

### API Endpoint

Plain English: this is the doorway that lets the browser ask for the queue.

Technical detail: `api/main.py:13-73` imports `build_review_queue`, lists `/review-queue` in the route index, and returns the payload directly from the new endpoint.

```python
from app.orchestrator import build_review_queue


@app.get("/review-queue")
def review_queue() -> dict[str, Any]:
    return build_review_queue()
```

This keeps the API thin. The route does not rebuild the queue itself. It delegates to the workflow layer, which keeps the data shape consistent with the rest of the app.

### Frontend Fetch And Render

Plain English: the page asks for queue data, then paints it into a table the user can scan.

Technical detail: `web/app.js:46-285` wires the queue DOM nodes, loads `/review-queue` during bootstrap, and rerenders the table on refresh or after workflow runs.

```javascript
async function loadReviewQueue() {
  setStatus(reviewQueueStatus, "Loading", "running");
  try {
    const response = await fetch("/review-queue");
    if (!response.ok) {
      throw new Error(`Queue request failed with status ${response.status}`);
    }
    const payload = await response.json();
    renderReviewQueue(payload);
    setStatus(reviewQueueStatus, "Ready", "success");
  } catch (error) {
    renderReviewQueueError(error);
    setStatus(reviewQueueStatus, "Queue error", "error");
  }
}
```

```javascript
function buildQueueRow(item) {
  const row = document.createElement("tr");
  row.appendChild(buildQueueCell(item.case_id, "queue-case"));
  row.appendChild(buildQueueCell(prettifyWorkflow(item.workflow_type), "queue-workflow"));
  row.appendChild(buildQueueCell(item.recommendation || "-", "queue-recommendation"));
  row.appendChild(buildQueueCell(item.risk_level || "-", `queue-risk ${mapQueueRiskKind(item.risk_level)}`));
  row.appendChild(buildQueueCell(item.reason_for_review || "-", "queue-reason"));
  row.appendChild(buildQueueCell(formatQueueTimestamp(item.timestamp_utc), "queue-time"));
  row.appendChild(buildQueueStatusCell(item.status || "Needs Review", mapQueueStatusKind(item.status)));
  return row;
}
```

The frontend is doing two jobs at once here: it fetches fresh data and it converts raw fields into a more readable operator table.

### Queue Panel Layout

Plain English: this is the section of the page that makes the queue look like a real work list instead of a debug dump.

Technical detail: `web/index.html:91-125` adds a dedicated queue panel above the sample cards, with a summary line, refresh action, table header, and meta footer.

```html
<section class="panel queue-panel" aria-label="Human review queue">
  <div class="panel-header queue-header">
    <div>
      <p class="eyebrow">Human review queue</p>
      <h2>Cases waiting on operator attention</h2>
    </div>
    <div class="queue-header-actions">
      <span class="status-pill" id="review-queue-status">Loading</span>
      <button type="button" class="secondary-button queue-refresh" id="review-queue-refresh">Refresh queue</button>
    </div>
  </div>
  ...
</section>
```

The placement matters. The queue appears early enough that the user sees the operational workflow before they get lost in sample detail.

### Queue Styling

Plain English: these styles make the queue readable, compact, and calm.

Technical detail: `web/styles.css:232-341` defines the table wrapper, row spacing, status color variants, and responsive behavior for smaller screens.

```css
.queue-table th,
.queue-table td {
  padding: 0.95rem 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  vertical-align: top;
}

.queue-status.success {
  color: #7ce6b1;
}

.queue-status.warning {
  color: #f1c85b;
}

.queue-status.error {
  color: #ff9a9a;
}
```

The colors are intentional. They make the queue feel like an operations board rather than a marketing page.

## What We Built

The project now has a dedicated human review queue built from real bundled workflow samples. A user can open the app, see which cases are still risky, and understand why they were routed that way without digging through the whole workflow response.

### Overview

When the app starts, it now requests `/review-queue`. The backend takes the bundled AP and AR samples, runs them through the workflow, and returns a compact queue payload. The browser then renders that payload as a table with risk, reason, and status visible up front.

The result is a better product story. The app no longer looks like a set of disconnected workflow demos. It now has a shared operator surface that pulls the AP and AR work into one place.

### Code Walkthrough

**`app/orchestrator/engine.py:52-335`**

Plain English: this file builds the queue from finished workflow cases and turns them into operator-friendly rows.

The queue builder is a thin layer over the real workflow results. That is important because it keeps the queue honest: the queue is not synthetic, it is derived from the same samples the app already understands.

**`api/main.py:13-73`**

Plain English: this file exposes the queue as a web endpoint.

The endpoint stays small on purpose. It does not duplicate queue logic, which keeps the app easier to test and easier to reason about.

**`web/index.html:91-125`**

Plain English: this file adds the queue panel to the page.

The panel is placed above the sample cards so the operator sees the queue first. That makes the interface feel like a work console rather than a gallery of examples.

**`web/app.js:46-285`**

Plain English: this file fetches queue data, turns it into table rows, and refreshes it after workflow actions.

This is where the queue becomes interactive. The refresh button lets the user pull the latest view without leaving the page.

**`web/styles.css:232-341`**

Plain English: this file gives the queue the visual shape of a finance table.

The styling keeps the rows compact, the labels readable, and the risk states easy to scan. That matters because this screen is meant to be used repeatedly.

### How The Pieces Connect

Plain English: first the backend builds queue rows, then the browser asks for them, then the table shows the items that need attention.

```text
[Sample fixtures]
       |
       v
[build_review_queue] --> [review queue JSON] --> [/review-queue endpoint] --> [web/app.js render]
                                                                |
                                                                v
                                                     [table in web/index.html]
```

That chain is small, but it is enough to make the product feel operational.

## Common Patterns

### Pattern 1: Convert Workflow Output Into A Different Shape

What it is for: turning a detailed workflow response into a short list item that a person can scan.

This is useful whenever the raw output is too verbose for an operator table. In this project, the queue row is a distilled version of the workflow result, not a second copy of it.

### Pattern 2: Keep Status Labels Human Friendly

What it is for: using queue labels like "Needs Review" and "Returned for Info" instead of exposing internal enum names.

This makes the product easier to explain and easier to demo. A recruiter does not need to decode internal state names to understand the workflow.

### Pattern 3: Refresh The Queue After Actions

What it is for: keeping the queue in sync after the user runs a sample or uploads a file.

That pattern matters because the queue is not static. It should reflect the latest cases, not only the initial page load.

## Edge Cases & Gotchas

1. **The queue endpoint can fail before the page loads**
   In plain English: if the Python environment is missing dependencies, the queue cannot build and the page shows an error instead of data.
   Technical cause: the backend imports the workflow stack before the route runs, so dependency problems appear as server errors.
   How to avoid: run the project with the repo virtual environment and keep dependency installation part of the smoke test.

2. **A queue row can be technically valid but still not useful**
   In plain English: a raw status like "review" is not enough on its own.
   Technical cause: queue consumers need a human-readable status and reason, not just the original decision object.
   How to avoid: always map workflow output into the queue-specific fields before rendering.

3. **A queue that only shows one case looks unfinished**
   In plain English: if the queue only ever shows a single sample, it does not feel like a real review surface.
   Technical cause: the operator view needs enough cases to show the range of AP and AR outcomes.
   How to avoid: build the queue from the full bundled sample set, not from just one demo path.

## How It Connects To Other Concepts

- **AP workflow review**: AP decisions become queue rows when they need human attention.
- **AR follow-up drafting**: AR escalation states show up in the same review surface.
- **Audit trail**: the queue uses timestamps and decision labels that come from workflow results.
- **Human-in-the-loop design**: the queue is the visible handoff between machine output and operator judgment.
- **Evaluation and demo flow**: the queue helps show that the product is not just extracting fields, it is managing decisions.

## Going Deeper

### Deterministic Demo Data

The queue is based on bundled samples, so it behaves the same way every time. That is ideal for demos because it lets the reviewer compare AP and AR cases without waiting for live data.

### Queue As A Product Boundary

The queue is more than a UI element. It is a boundary that separates machine suggestions from human decisions. That boundary is what makes the app feel safe enough for finance use.

### Why The Queue Lives In The Workflow Layer

The queue is built in the workflow layer instead of the browser because it depends on decisions, review flags, and audit data. Putting that logic in one place keeps the frontend simple and keeps the rules testable.

## Quick Reference

### Key Terms

| Term | Plain English meaning | Technical meaning |
|------|-----------------------|-------------------|
| Queue item | One case waiting for attention | A normalized review row built from workflow output |
| Risk level | How serious the case feels | A label derived from the human review state |
| Status | What the operator should do next | A queue-facing decision label like Approved or Needs Review |
| Reason for review | Why the case was flagged | A short summary built from workflow flags and decision data |
| Review endpoint | The browser's source of queue data | `GET /review-queue` |

### Essential Patterns

```python
queue = build_review_queue()
```

```javascript
const response = await fetch("/review-queue");
```

```html
<section class="panel queue-panel" aria-label="Human review queue">
```

---

*Generated: 2026-05-28 | Project: invoiceflow-ai | Files: app/orchestrator/engine.py, api/main.py, web/index.html, web/app.js, web/styles.css*
