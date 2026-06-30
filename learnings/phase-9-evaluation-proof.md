# Phase 9: Evaluation Proof

> Phase 9 made evaluation visible as credibility proof without letting it take over the product experience.

---

## In Plain English

Before this phase, InvoiceFlow already had evaluation logic and a UI dashboard, but the README and app needed cleaner framing. A reviewer should quickly see that the project is tested, while a normal user should still focus on the main finance workflow.

Phase 9 added a compact five-case evaluation table to the README and softened the evaluation tab in the UI. The README now shows expected result, actual result, and pass status for the five main demo cases. The app now labels the eval area as “Evaluation Proof” and styles metrics as secondary proof instead of a dominant dashboard.

This matters because AI workflow projects need proof. But proof should support the product story, not bury it under metrics.

## The Problem It Solves

The project needed to communicate:

```text
This workflow is tested
  without making the app feel academic
```

The best balance was:

- README: show compact eval proof early in the technical section.
- UI: keep eval visible but visually secondary.
- Product path: still lead with AP/AR workflow, recommendation, evidence, and review.

## What We Built

### Step 23: Compact Evaluation Table

Plain English: The README now shows reliability proof before technical commands.

The table added:

```markdown
| Eval case | Expected | Actual | Status |
| --- | --- | --- | --- |
| Clean Invoice | `approve` | `approve` | Pass |
| Missing PO Invoice | `request_missing_info` | `request_missing_info` | Pass |
| Duplicate Invoice Risk | `human_review` | `human_review` | Pass |
| High-Value Approval Required | `manager_review` | `manager_review` | Pass |
| AR Overdue Follow-Up | `draft_follow_up` | `draft_follow_up` | Pass |
```

Technical detail: This table is intentionally compact. The detailed eval commands and thresholds still exist below it, but the first thing a reviewer sees is that the core demo path is checked.

### Step 24: Keep Eval UI Secondary

Plain English: The evaluation tab now reads like supporting proof, not the main product.

The tab heading changed from dashboard language:

```html
<p class="eyebrow">Evaluation Dashboard</p>
<h2>Reliability checks and latest eval results</h2>
```

to product-support language:

```html
<p class="eyebrow">Evaluation Proof</p>
<h2>Quality gates behind the workflow</h2>
```

The intro now explains its role:

```html
Evaluation stays secondary to the operator workflow. Use it to confirm routing, extraction, citation, review, and AR draft quality after the demo path is clear.
```

The metric grid was visually softened:

```css
.eval-summary-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px 18px;
  padding: 14px 0 4px;
  border-top: 1px solid rgba(31, 39, 33, 0.08);
  border-bottom: 1px solid rgba(31, 39, 33, 0.06);
}

.eval-metric strong {
  font-size: 1rem;
}
```

Technical detail: This keeps eval metrics visible but less visually loud than the decision surface.

## How The Pieces Connect

The product credibility flow now works like this:

```text
User sees product workflow
        |
        v
User runs AP/AR demo
        |
        v
User sees decision, evidence, review gate
        |
        v
User can open Evaluation Proof
        |
        v
Technical reviewer sees quality gates and README proof
```

Evaluation is no longer hidden, but it is also not the first thing the product asks the user to understand.

## Common Patterns

### Pattern 1: Show Proof Before Commands

What it is for: Help reviewers understand the result before making them run tools.

A table of expected vs actual results is faster to understand than a list of CLI commands.

### Pattern 2: Keep Evals Product-Supporting

What it is for: Avoid turning the product into an academic dashboard.

Evaluation should prove reliability, not replace the workflow demo.

### Pattern 3: Compact Metrics

What it is for: Show engineering discipline without clutter.

The eval tab still shows routing, extraction, citation, grounding, review, AR, and latency metrics, but the visual style is quieter.

## Edge Cases & Gotchas

### 1. Eval proof can become too technical

In plain English: A recruiter should not need to know every metric before understanding the app.

Technical cause: AI projects often overexpose eval internals too early.

How to avoid: Put compact proof first, detailed commands second.

### 2. UI eval dashboards can dominate the product

In plain English: The main experience is invoice review, not metric browsing.

Technical cause: Large metric cards and dashboard language shift attention away from the operator workflow.

How to avoid: Use “proof” framing and quieter visual styling.

### 3. Expected labels should match user language

In plain English: `request_missing_info` is clearer than raw backend code when used as product proof.

Technical cause: Backend enums are not always the best user-facing labels.

How to avoid: Use labels that reflect visible operator actions.

## Quick Reference

### Files Changed In Phase 9

- `README.md`
  - Added compact five-case eval proof table.

- `web/index.html`
  - Reframed evaluation tab as Evaluation Proof.
  - Clarified that evaluation supports the operator workflow.

- `web/styles.css`
  - Quieted eval metrics with smaller type, fewer columns, and subtle separators.

- `steps.md`
  - Logged Steps 23 and 24.

### Phase 9 Commits

- `db7d4d8 docs: add compact eval proof`
- `fe295d2 docs: log eval table step`
- `231ec1a quiet eval proof panel`
- `3146f17 docs: log eval ui step`

### Beginner Test

Can a beginner human understand this page as it goes?

Mostly yes. A beginner does not need to start with the eval tab, but if they open it, the wording now explains that it is reliability proof behind the workflow. The README also makes the five tested cases easy to understand.

## Updates

- 2026-06-30 - Created after Phase 9 to document the compact eval proof table and secondary eval UI treatment.
