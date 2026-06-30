# Phase 10: Screenshots And Demo Assets

> This phase made InvoiceFlow easier to understand without a live explanation by adding fresh product screenshots and a guided demo script.

---

## In Plain English

This phase is about presentation. The app already had real workflows, evidence, review gates, and evaluation proof, but a person looking at the repo still needed to run the project and explore it on their own. That is risky because most recruiters and clients do not explore software randomly. They look for a quick signal that the project is real, useful, and easy to understand.

The screenshots act like a photo tour of the product. They show the entry screen, AP result, evidence panel, human review queue, evaluation proof, and AR follow-up. The demo script acts like a guided path. It tells someone what to click, what to notice, and how to explain the project in a short presentation.

Together, these assets make InvoiceFlow feel more like a finished product. A viewer can see what the app does before reading code, and the person presenting the project has a clean story to follow.

## What Is A Demo Asset Phase?

A demo asset phase packages working software so other people can understand it quickly. It does not add new product logic. Instead, it creates the materials that help the product communicate: screenshots, walkthroughs, demo steps, and presentation language.

For InvoiceFlow, this matters because the product has several layers:

- AP invoice review
- AR follow-up drafting
- structured extraction
- policy evidence
- risk/anomaly checks
- human review
- audit metadata
- evaluation proof

Without a guided demo path, these can feel like disconnected technical blocks. With a guided path, they become one clear story:

```text
Select case
  -> Extract facts
  -> Check policy
  -> Detect risk
  -> Recommend action
  -> Route to human review
  -> Preserve audit trail
```

## The Problem It Solves

Before this phase, the project depended too much on the viewer understanding the app by exploration. That creates three problems.

First, the viewer may click the wrong thing first. If they open a debug or evaluation area before seeing a decision, the app can feel technical before it feels useful.

Second, screenshots can become stale. If the README or portfolio shows an older UI, it weakens trust because the product looks inconsistent.

Third, the explanation can become too backend-heavy. InvoiceFlow has real engineering depth, but the first impression should be product value: finance teams can review risky invoices and overdue cases with evidence.

Phase 10 fixes this by giving the repo current screenshots and a demo script that starts with the product story before the technical details.

## What We Built

### Fresh Screenshot Set

Plain English: The screenshots show the app as it currently looks, so someone can understand the product without running it first.

Files created:

```text
docs/screenshots/operator-console.png
docs/screenshots/ap-result.png
docs/screenshots/evidence-panel.png
docs/screenshots/human-review-queue.png
docs/screenshots/eval-dashboard.png
docs/screenshots/ar-follow-up.png
```

Each screenshot has a specific job:

| Screenshot | What it proves |
|---|---|
| `operator-console.png` | The app starts with a centered product entry and clear AP/AR explanation. |
| `ap-result.png` | The app shows the recommendation before raw details. |
| `evidence-panel.png` | The decision can be traced to extracted fields, anomalies, and policy evidence. |
| `human-review-queue.png` | Risky cases are routed into a review queue instead of treated as final. |
| `eval-dashboard.png` | The workflow has measurable reliability proof. |
| `ar-follow-up.png` | The product also handles AR follow-up drafting, not just AP invoices. |

### Guided Demo Path

Plain English: The demo path tells someone exactly how to show the project without getting lost.

File changed:

```text
docs/showcase.md
```

The new path is:

```text
1. Open the app.
2. Start at the operator entry screen.
3. Explain AP and AR.
4. Run Missing PO Invoice.
5. Read the decision-first result.
6. Open Evidence & Reasoning.
7. Open Human Review & Audit.
8. Run AR Overdue Follow-Up.
9. Show the AR follow-up draft.
10. Open Evaluation.
```

This order matters because it teaches the viewer in the same order a real operator would care:

```text
What is this?
What case am I reviewing?
What should I do?
Why?
Does a person need to check it?
Can the system handle AR too?
Is this tested?
```

## How It Works

### Screenshot Capture

Plain English: The screenshots were captured from the actual local app, not mocked by hand.

The app was available at:

```text
http://127.0.0.1:8000/ui
```

The browser was used to move through real UI states:

```text
open page
capture operator console
run Missing PO Invoice
capture AP result
open Evidence & Reasoning
capture evidence panel
open Human Review & Audit
capture review queue
open Evaluation
capture eval proof
run AR Overdue Follow-Up
capture AR result
```

This matters because screenshots should reflect the real app state. A fake screenshot can look polished but create trust problems when the live app looks different.

### Demo Script Rewrite

Plain English: The script now says what to click and what to say in a human way.

The old script leaned more technical. It talked early about FastAPI, guardrails, self-healing retrieval, and tool-call orchestration. Those details are valuable, but they should not be the first thing a non-technical viewer hears.

The rewritten script starts with:

```text
This is InvoiceFlow AI, a finance operations console for two common workflows:
AP invoice review and AR overdue follow-up.
```

That is easier to understand because it explains the product category first. Then the script explains the product promise:

```text
upload or select a case
extract the facts
check policy evidence
detect risk
recommend an action
keep a human-review trail
```

The technical depth remains available later through evidence, audit, and evaluation sections.

## How The Pieces Connect

Plain English: Screenshots and the demo script work together like a map and a tour guide.

```text
README / portfolio visitor
        |
        v
screenshots show the product visually
        |
        v
docs/showcase.md explains the path
        |
        v
live app demonstrates AP and AR workflows
        |
        v
evidence, review, audit, and eval prove depth
```

The screenshots create fast visual trust. The demo script creates narrative trust. The live app creates functional trust.

## Common Patterns

### Pattern 1: Product First, Engineering Second

What it is for: Make the project understandable before showing implementation details.

In InvoiceFlow, the demo starts with:

```text
finance operations console
AP invoice review
AR overdue follow-up
evidence-backed decisions
human review
```

Only after that does it mention technical proof:

```text
retrieval
guardrails
audit metadata
evaluation results
```

This ordering is important for portfolio projects. A recruiter or client needs to understand what the product does before they care how it was built.

### Pattern 2: One Screenshot, One Job

What it is for: Avoid screenshots that all show the same thing.

Each screenshot should prove a different product capability:

```text
entry screen -> positioning
AP result -> decision-first design
evidence panel -> explainability
review queue -> human-in-the-loop safety
eval dashboard -> reliability thinking
AR follow-up -> second workflow
```

This makes the screenshot set more useful than a random gallery.

### Pattern 3: Guided Demo Path

What it is for: Prevent the viewer from getting confused by too many possible clicks.

The best demo path intentionally focuses on one strong AP case and one strong AR case. It does not try to show every sample. That keeps the story focused:

```text
Missing PO Invoice -> demonstrates AP risk and policy evidence
AR Overdue Follow-Up -> demonstrates customer follow-up and escalation
Evaluation -> demonstrates reliability proof
```

## Edge Cases & Gotchas

### Stale Screenshots

In plain English: Screenshots can quietly become wrong after UI changes.

Technical cause: Static image files do not update automatically when `web/index.html`, `web/styles.css`, or `web/app.js` changes.

How to avoid: Refresh screenshots after major UI phases and before portfolio publishing.

### Over-Technical Demo Scripts

In plain English: If the first sentence sounds like an architecture diagram, non-technical viewers may stop listening.

Technical cause: Engineering-heavy projects often lead with backend mechanisms instead of product outcomes.

How to avoid: Start with the user workflow, then show the technical proof once the viewer understands the product.

### Too Many Demo Cases

In plain English: More examples can make the product harder to understand, not easier.

Technical cause: Each additional case adds another branch the viewer has to mentally track.

How to avoid: Keep the primary demo to five visible cases, and only present two in the fast walkthrough.

### Capturing The Wrong State

In plain English: A screenshot of an empty app does not prove the product works.

Technical cause: Some useful UI panels only populate after running a workflow or opening a tab.

How to avoid: Capture each screenshot after the correct user action has been performed.

## Why This Improves InvoiceFlow

Phase 10 improves InvoiceFlow in three ways.

First, it makes the repo easier to scan. A reviewer can open screenshots and understand the shape of the product quickly.

Second, it makes the demo repeatable. The presenter no longer has to improvise what to click or say.

Third, it keeps the product story focused. The viewer sees the same progression everywhere:

```text
AP/AR case
facts
policy evidence
risk
recommendation
human review
audit
evaluation
```

## How It Connects To Other Concepts

- **README case study**: Screenshots make the README feel more concrete.
- **Operator entry screen**: The first screenshot proves the app has a clear first impression.
- **Evidence transparency**: The evidence screenshot proves RAG is visible without jargon.
- **Human review queue**: The review screenshot proves risky outputs are not treated as final.
- **Evaluation proof**: The eval screenshot shows reliability thinking without forcing the viewer into terminal commands.
- **Portfolio presentation**: The walkthrough script gives a clean spoken story for interviews and client demos.

## Going Deeper

### Automated Screenshot Tests

Plain English: The app could automatically capture screenshots during CI so docs stay fresh.

This would require a browser automation setup, such as Playwright, that runs the app, clicks through the demo path, and saves images.

### Short Demo Video

Plain English: A video can show motion and flow better than static screenshots.

For portfolio use, a 60-90 second recording should follow the same path from `docs/showcase.md`.

### Screenshot Links In README

Plain English: The README should guide the viewer through the screenshot set in order.

This makes the README feel like a case study instead of a list of files.

## Quick Reference

### Key Terms

| Term | Plain English meaning | Technical meaning |
|---|---|---|
| Demo path | The order someone should click through the app | A scripted user journey through product states |
| Screenshot asset | A saved image of the app | Static PNG documentation generated from the UI |
| Operator entry | The first product screen | The top-level `/ui` state before a workflow run |
| Decision-first result | The answer appears before details | Recommendation, reason, risk, review, and evidence summary are prioritized |
| Evidence panel | Shows why the answer is supported | Retrieved policy, citations, anomalies, and extracted fields |
| Review queue | Shows cases needing a person | Human-in-the-loop case list with status and reason |
| Evaluation proof | Shows reliability checks | Metrics and pass/fail results for workflow quality |

### Files Changed In This Phase

```text
docs/screenshots/operator-console.png
docs/screenshots/ap-result.png
docs/screenshots/evidence-panel.png
docs/screenshots/human-review-queue.png
docs/screenshots/eval-dashboard.png
docs/screenshots/ar-follow-up.png
docs/showcase.md
steps.md
```

### Best Demo Sentence

```text
InvoiceFlow AI helps finance teams review invoices and overdue cases faster by extracting facts, checking policy evidence, recommending the next action, routing risky cases to human review, and preserving an audit trail.
```

### Best Demo Order

```text
Operator entry
  -> Missing PO Invoice
  -> Decision-first AP result
  -> Evidence & Reasoning
  -> Human Review & Audit
  -> AR Overdue Follow-Up
  -> Evaluation
```

## Quiz Questions

1. Why should the demo start with product value before technical architecture?
2. What does each screenshot in Phase 10 prove?
3. Why is a guided demo path better than letting a recruiter explore randomly?
4. Why should raw JSON/debug details stay out of the main demo path?
5. How do screenshots and `docs/showcase.md` work together?

---

*Generated: 2026-06-30 | Project: invoiceflow-ai | Files: docs/screenshots/*, docs/showcase.md, steps.md*
