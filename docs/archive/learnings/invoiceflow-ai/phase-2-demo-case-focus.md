# Phase 2 Demo Case Focus

> How InvoiceFlow AI was narrowed to five clear demo cases so the product feels focused instead of scattered.

---

## In Plain English

This phase made the demo easier to understand. Before this pass, InvoiceFlow had
several useful sample fixtures, but the visible product did not clearly say
which ones mattered most. That can make a project feel like a collection of
experiments instead of a product.

Phase 2 focused the visible UI and README around five strong cases: Clean
Invoice, Missing PO Invoice, Duplicate Invoice Risk, High-Value Approval
Required, and AR Overdue Follow-Up. These five cases are enough to show the
main product value without overwhelming the user.

The important idea is that backend capability and demo presentation are not the
same thing. The backend can keep extra fixtures for evals and testing, but the
main product surface should guide the user through the clearest story.

## What Is Demo Case Focus?

Demo case focus means choosing a small number of examples that teach the product
well. A portfolio viewer or client should not have to inspect every fixture to
understand what the product does.

For InvoiceFlow AI, each visible case now proves one finance control:

- Clean Invoice proves the approve path.
- Missing PO Invoice proves missing-information handling.
- Duplicate Invoice Risk proves risk detection.
- High-Value Approval Required proves approval-threshold review.
- AR Overdue Follow-Up proves receivables follow-up drafting.

This turns the demo from "try some samples" into a guided product walkthrough.

## The Problem It Solves

Too many visible examples can create confusion. A user may ask:

- Which case should I run first?
- Why are there multiple AR examples?
- Which sample proves the strongest product idea?
- Is this a product or just a test harness?

The answer is to show fewer cases, but make each one count. Five cases gives
InvoiceFlow enough range without making the UI feel like a dataset browser.

## How It Works

Plain English: the UI now presents five named cases, and the README uses those
same names.

```text
UI sample cards
  -> five curated case names
  -> sample IDs hidden behind buttons
  -> friendly running status
  -> README table with matching names
```

The backend still knows about all sample files. Phase 2 did not delete fixtures
or reduce evaluation coverage. It only changed the visible product story.

### The Five Visible Cases

Plain English: each case exists to prove one part of the product.

| Case | Workflow | What it proves |
| --- | --- | --- |
| Clean Invoice | AP | The system can approve a normal invoice when key checks pass. |
| Missing PO Invoice | AP | The system separates missing information from rejection. |
| Duplicate Invoice Risk | AP | The system flags duplicate payment risk. |
| High-Value Approval Required | AP | The system routes threshold cases to review. |
| AR Overdue Follow-Up | AR | The system drafts a safe customer follow-up. |

This set is intentionally small. It covers the main AP and AR story without
turning the UI into a long list.

### AP And AR Explanation

Plain English: the UI now explains finance abbreviations at the moment the user
needs them.

The hero now says:

```text
AP means Accounts Payable: review vendor invoices before the company pays them.
AR means Accounts Receivable: follow up on overdue customer payments safely.
```

The upload workflow selector also uses plain labels:

```text
AP - vendor invoice review
AR - overdue payment follow-up
```

That matters because users should not need finance vocabulary before they can
use the app.

### README Alignment

Plain English: the README now uses the same case names as the app.

The technical sample table now maps product names to sample IDs:

```text
Clean Invoice -> ap_001_clean_invoice
Missing PO Invoice -> ap_002_missing_po
Duplicate Invoice Risk -> ap_004_duplicate_invoice
High-Value Approval Required -> ap_003_threshold_review
AR Overdue Follow-Up -> ar_003_payment_claim_no_proof
```

This removes a common demo problem: instructions that use one label while the
UI shows another.

## What We Built

Phase 2 modified three files:

```text
web/index.html
web/app.js
README.md
```

It also updated the project step log:

```text
steps.md
```

### Step 5: Five Visible Demo Cases

Plain English: the UI now gives users five clear options instead of a loose
sample area.

Changed files:

```text
web/index.html
web/app.js
```

The sample card area now shows:

- Clean Invoice
- Missing PO Invoice
- Duplicate Invoice Risk
- High-Value Approval Required
- AR Overdue Follow-Up

The JavaScript also has a `visibleDemoCases` map so status messages can show
friendly case names instead of raw IDs.

### Step 6: Plain AP/AR Language

Plain English: the UI now defines the finance abbreviations before asking the
user to choose a workflow.

Changed file:

```text
web/index.html
```

The hero text and upload dropdown now explain the two workflow types in plain
language.

### Step 7: README Case Name Alignment

Plain English: the README now matches the app.

Changed file:

```text
README.md
```

The older raw sample list was replaced by a five-case table with UI case name,
sample ID, and expected result.

## How The Pieces Connect

Plain English: the app and README now speak the same product language.

```text
README Best Demo Path
        |
        v
README five-case table
        |
        v
UI sample cards
        |
        v
Backend sample IDs
        |
        v
Existing workflow engine
```

This means a viewer can read the README, open the app, and recognize the same
case names immediately.

## Common Patterns

### Pattern 1: Curate The Demo, Keep The Fixtures

What it is for: keeping a product simple without deleting useful test data.

The backend can keep seven fixtures for evals and review queues, but the UI can
show five curated cases. This keeps reliability coverage while making the demo
easier to understand.

### Pattern 2: Use Product Names Before Internal IDs

What it is for: making technical samples feel like product workflows.

`ap_002_missing_po` is useful for code. `Missing PO Invoice` is useful for
humans. Both can exist, but the UI should show the human-friendly name first.

### Pattern 3: Define Jargon At The Point Of Use

What it is for: helping beginners without adding long explanations.

AP and AR are common finance terms, but the page should not assume users know
them. A short definition near the workflow selector removes confusion.

## Edge Cases And Gotchas

### Gotcha 1: Too Many Cases Looks Impressive But Feels Confusing

In plain English: more examples can make the product harder to understand.

Technical cause: every extra visible sample adds another choice the user has to
interpret.

How to avoid: keep the primary UI focused on the five strongest cases.

### Gotcha 2: README And UI Names Drift Apart

In plain English: a viewer gets confused when instructions do not match the
screen.

Technical cause: sample IDs and display labels are maintained in different
places.

How to avoid: update README and UI case names together whenever the demo set
changes.

### Gotcha 3: Backend Fixtures Are Not The Same As Product Cases

In plain English: not everything in the repo needs to be on the first screen.

Technical cause: evaluation datasets often need extra scenarios that are useful
for testing but not ideal for a clean demo.

How to avoid: keep extra fixtures available behind the scenes and expose only
the curated product cases in the main UI.

## How It Connects To Other Concepts

- **Phase 1 README case study**: Phase 2 makes the app match the cleaner story
  from the README.
- **Case detail redesign**: Phase 3 can now build around a smaller, more
  predictable set of demo outcomes.
- **Evaluation proof**: The eval dataset can remain broader than the visible
  case selector.
- **Human review**: The five cases include approve, missing information, review,
  duplicate risk, threshold review, and AR drafting.

## Going Deeper

### Demo Information Architecture

Demo information architecture is about deciding what the user sees first, what
stays secondary, and what remains available only for technical review. Phase 2
uses that idea by separating visible cases from backend fixtures.

### Beginner-Friendly Product Language

Beginner-friendly language does not mean removing technical depth. It means the
first layer uses words a non-specialist can follow, while technical detail stays
available later.

## Quick Reference

### Five Visible Cases

```text
Clean Invoice
Missing PO Invoice
Duplicate Invoice Risk
High-Value Approval Required
AR Overdue Follow-Up
```

### Case ID Mapping

```text
Clean Invoice -> ap_001_clean_invoice
Missing PO Invoice -> ap_002_missing_po
Duplicate Invoice Risk -> ap_004_duplicate_invoice
High-Value Approval Required -> ap_003_threshold_review
AR Overdue Follow-Up -> ar_003_payment_claim_no_proof
```

### AP And AR Definitions

```text
AP means Accounts Payable: review vendor invoices before the company pays them.
AR means Accounts Receivable: follow up on overdue customer payments safely.
```

## Beginner Understandability Check

Can a beginner human understand the page as it goes?

Mostly yes for Phase 2.

The visible demo choices are now clearer, AP and AR are defined in the UI, and
the README uses the same case names as the product. A beginner should now know
what the five main cases are and why they exist.

What still needs work is the page structure after a case runs. The result area
still has multiple panels and technical sections, so Phase 3 should make the
case detail view more decision-first and less scattered.

## Updates

- 2026-06-30 - Created after Phase 2 to document the five-case demo focus,
  AP/AR explanation pass, README/UI case-name alignment, and remaining result
  page clarity work.
