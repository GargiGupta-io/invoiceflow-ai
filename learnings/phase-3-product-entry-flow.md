# Phase 3 Product Entry Flow

> How InvoiceFlow AI's first screen was reshaped into a centered product entry with clearer upload intake and staged workflow loading.

---

## In Plain English

This phase improved the first thing a user sees. Before this pass, the page had
a centered hero, but the workflow state and sample snapshot sat below it like a
separate dashboard strip. Upload was technically near the top, but it still
looked like a plain form.

Phase 3 made the top of the page feel more like one product entry point. The
user now sees the product promise, AP/AR explanation, upload controls, sample
actions, status, sample chips, and latest audit information together.

The loading cue also became more useful. Instead of one static message, it now
steps through the workflow stages so the user understands that InvoiceFlow is
reading the case, extracting facts, retrieving policy, checking risk, and
preparing a recommendation.

## What Is A Product Entry Flow?

A product entry flow is the first interaction path a user sees. It answers:

1. What is this product?
2. What can I do first?
3. What happens after I click?

For InvoiceFlow AI, the entry flow should be:

```text
Read product promise
  -> understand AP/AR
  -> upload a document or run a sample
  -> watch staged processing cue
  -> land in the result workspace
```

This phase focused on that first path.

## The Problem It Solves

Even a useful AI workflow can feel confusing if the first screen is scattered.
When upload, sample buttons, status, and audit state feel like separate blocks,
the user has to mentally assemble the product flow.

The fix is to make the first screen feel like one composed entry area. The user
should not wonder where to begin or what the app is doing while it works.

## How It Works

Plain English: the hero now contains the full starting surface.

```text
Hero
  -> product promise
  -> AP/AR explanation
  -> intake label
  -> upload row
  -> loading cue
  -> sample actions
  -> operator snapshot
```

The lower workspace is still available after a run, but the first screen now has
a clearer job: start the workflow.

### Centered Entry

Plain English: the first screen now feels like one centered console entry.

The operator snapshot was moved inside the hero:

```text
Workflow State
Sample Cases
Latest Audit
```

This means the user sees upload, sample actions, workflow state, and latest
audit together instead of as separate stacked sections.

### Upload Intake Row

Plain English: upload now looks like a real starting action.

The page adds this cue:

```text
Start with a document, or run one of the sample cases.
```

Then the upload row shows:

```text
Workflow type
Document file
Upload and run
```

The row has subtle top and bottom rules, which gives it a stronger position
without turning it into a heavy card.

### Staged Loading Cue

Plain English: the app now tells the user what it is doing while a run is in
progress.

The sequence is:

```text
Reading or uploading
  -> Extracting key facts
  -> Retrieving policy evidence
  -> Checking risk signals
  -> Preparing recommendation
```

This is frontend-only. It does not change backend timing or logic. It gives the
user a better mental model of the pipeline while the request is running.

## What We Built

Phase 3 modified:

```text
web/index.html
web/styles.css
web/app.js
steps.md
```

### Step 8: Centered Product Entry

Plain English: the top screen became one focused starting area.

Changed files:

```text
web/index.html
web/styles.css
```

The operator snapshot moved into the hero. CSS now gives the hero a taller,
centered layout and constrains the snapshot width.

### Step 9: Upload Intake Row

Plain English: upload became visibly part of the main first action.

Changed files:

```text
web/index.html
web/styles.css
```

The upload controls now have an intake label and subtle horizontal rules. This
makes the form feel less like a random field group and more like the product's
entry point.

### Step 10: Staged Loading Cue

Plain English: loading now explains the workflow stages.

Changed file:

```text
web/app.js
```

The existing loading cue is reused. A timer updates the loading text while the
request is in flight, and the timer is cleared when the workflow finishes or
fails.

## How The Pieces Connect

Plain English: the first screen now behaves like a guided intake desk.

```text
User chooses sample or upload
        |
        v
Loading cue starts
        |
        v
Stage text cycles through workflow steps
        |
        v
Backend returns result
        |
        v
Loading cue hides and workspace appears
```

The UI does not pretend the frontend is doing the backend work. It simply gives
the user readable progress language while the workflow request is active.

## Common Patterns

### Pattern 1: One Entry Surface

What it is for: reducing first-screen confusion.

Instead of separating hero, upload, status, and snapshot into separate bands,
combine them into one coherent starting area.

### Pattern 2: Lightweight Progress Copy

What it is for: explaining invisible backend work.

Users cannot see extraction, retrieval, validation, or decisioning happen
directly. Short staged messages help them understand the pipeline without
showing technical logs.

### Pattern 3: Keep Motion Meaningful

What it is for: adding polish without distracting the user.

The loading cue changes because the workflow is running. It is not decorative
motion for its own sake.

## Edge Cases And Gotchas

### Gotcha 1: Loading Stages Are Approximate

In plain English: the staged text is a helpful guide, not a live backend event
stream.

Technical cause: the current backend returns one response after the workflow is
complete. It does not stream per-stage events.

How to avoid confusion: keep the messages general and use them as progress
language, not exact telemetry.

### Gotcha 2: Duplicate CSS Rules Can Override Earlier Styling

In plain English: a later rule in the stylesheet can quietly undo a style
change.

Technical cause: `web/styles.css` has repeated `.hero-upload` rules. Phase 3
updated both relevant rules so the intended upload styling wins.

How to avoid: search for duplicate selectors before assuming a CSS change is
active.

### Gotcha 3: Moving DOM Elements Can Break JS If IDs Change

In plain English: moving an element is safe only if the code can still find it.

Technical cause: `web/app.js` uses IDs such as `entry-workflow-state`,
`entry-sample-count`, and `entry-audit-state`.

How to avoid: move the same elements without renaming their IDs unless the JS is
updated too.

## How It Connects To Other Concepts

- **Phase 1 README story**: The UI now better matches the product-first story.
- **Phase 2 demo focus**: The five sample chips are now part of the hero entry.
- **Phase 4 case detail work**: The next phase should make the post-run result
  as clear as the entry screen.
- **Workflow transparency**: The staged loading cue previews the pipeline that
  later evidence/result panels should explain.

## Going Deeper

### Real Streaming Progress

A future version could stream backend stage events through Server-Sent Events or
WebSockets. That would make the loading cue reflect actual extraction,
retrieval, validation, and decision completion.

### First-Screen Conversion Design

This is the idea of making one action path obvious. For InvoiceFlow, that action
is upload a document or run a sample case.

## Quick Reference

### Entry Flow

```text
Hero promise
  -> AP/AR definitions
  -> intake label
  -> upload row
  -> sample actions
  -> operator snapshot
```

### Loading Stages

```text
Reading/uploading
Extracting key facts
Retrieving policy evidence
Checking risk signals
Preparing recommendation
```

## Beginner Understandability Check

Can a beginner human understand the page as it goes?

Mostly yes for the first screen.

The entry area now gives a beginner a clearer path: understand the product,
choose upload or sample, and watch the workflow stages while the system works.
The remaining confusing area is after the result appears, where decision,
evidence, review, audit, and debug information still need a cleaner
decision-first layout.

## Updates

- 2026-06-30 - Created after Phase 3 to document the centered product entry,
  upload intake row, staged loading cue, and remaining result-page clarity work.
