# Phase 15H: Current Hero, Guide Cards, And Product Path

> The top of InvoiceFlow now uses a full-width product hero, a guided sample section, and a four-stage Product Path that controls the main workflow views.

---

## In Plain English

This document describes the current InvoiceFlow interface, not the older visual experiments that have been replaced.

The page now starts like a real product page: the hero spans the full browser width, the aurora background is a visible ribbon rather than a boxed poster, and the main content is still kept readable inside controlled inner widths.

The page is meant to guide a first-time viewer in this order before a case is selected:

1. Understand the product promise.
2. Understand AP and AR.
3. Start a review by uploading a file or running a sample.
4. Read the “What's inside?” cards.
5. Use the Product Path to open Summary, Evidence, Review, or Evaluation.

After a case is selected, the page intentionally shortens the route. The “What's inside?” teaching cards collapse away, the Product Path becomes compact, and the case result appears sooner.

## What Changed

### Full-Width Hero

Plain English: the hero no longer looks like a card with hard side borders.

The page shell was widened so the hero can span the full viewport. The content inside the hero is still constrained so the text and form do not stretch too wide.

This makes the top of the page feel more like a polished product site instead of a student project section.

### Soft Aurora Background

Plain English: the background now has a visible single-line glow ribbon inspired by the React Bits Soft Aurora component.

The project does not have a React frontend layer, so the aurora is implemented as a small standalone canvas script rather than adding a full React/Vite setup just for one visual effect.

The aurora uses InvoiceFlow colors:

- soft green
- warm amber
- cream highlight

It should feel creative, but still calm enough for a finance workflow product. The line also reacts to cursor movement across the hero by shifting its bright highlight toward the pointer.

### Start The Review

Plain English: this section tells the user where to begin.

`Start the review` is now a real heading, not a tiny label. On desktop it aligns with the upload form so the section reads like one connected block.

The upload row keeps:

- AP/AR workflow selector
- file picker
- upload button
- small OCR/text fallback note

### What's Inside

Plain English: this section explains the three cards below it.

The heading separates the guide cards from the upload form. Without it, the cards looked like random boxes attached to the form.

The three cards are:

- `Current Case`
- `Sample Cases`
- `Latest Decision`

Before a workflow runs, they teach the user what the product does. After a workflow runs, they become live summaries.

### Current Case Card

Plain English: this card explains the path from choosing a case to getting a recommendation.

Before a run it shows:

- Choose AP invoice or AR follow-up
- Extract vendor/customer/amount
- Check policy and risk signals
- Decide approve/review/follow-up

After a run it updates with:

- AP or AR desk
- vendor or customer
- amount
- recommendation

### Sample Cases Card

Plain English: this is the fastest way to demo the product.

It shows five curated cases:

- Clean Invoice
- Missing PO
- Duplicate Risk
- High-Value
- AR Overdue

The `Run sample` label is plain text now, not a pill. The sample buttons have enough vertical room, and the fade overlay no longer blocks the AR Overdue button.

### Latest Decision Card

Plain English: this card shows whether the output is evidence-backed and review-safe.

Before a run it explains:

- recommendation is evidence-first
- policy evidence matters
- human review gate matters
- extraction, policy, and decision form a mini audit trail

After a run it updates with:

- recommendation
- evidence count
- review gate status
- mini audit timeline

### Product Path Navigation

Plain English: the old separate Product Path and tab row have been merged.

There is now one four-stage navigation:

- `Case Summary` - Invoice + Extract
- `Evidence` - Policy + Risk
- `Review` - Decision + Audit
- `Evaluation` - Quality checks

Clicking these stages changes the main workspace panel. This avoids showing two competing navigation rows that seemed to mean the same thing.

After a case is selected, the large Product Path headline is hidden. The user still gets the four clickable stages, but the screen prioritizes the recommendation first.

### Five-Case Demo Scope

Plain English: the visible product demo now matches the story.

The backend can still keep extra internal samples, but the visible UI focuses on the five curated cases:

- Clean Invoice
- Missing PO Invoice
- Duplicate Invoice Risk
- High-Value Approval Required
- AR Overdue Follow-Up

This affects:

- the sample launcher
- the review queue display
- the evaluation dashboard summary

The point is to avoid telling a recruiter “five curated cases” in one place and then showing seven cases somewhere else.

### Shorter Result Path

Plain English: after clicking a sample, the result gets priority.

Before this update, the user had to pass through too much intro content before the decision appeared. Now, when a workflow completes, the page adds a `case-selected` state. That state hides the guide-card section, compacts the Product Path, and scrolls the user to the decision summary.

The intended experience is:

1. Choose or upload a case.
2. See the recommendation quickly.
3. Inspect why it happened.
4. Open evidence, review, audit, or eval only when needed.

### Progressive Disclosure For Evidence And Eval

Plain English: proof is still available, but it is no longer forced into the first read.

The Evidence section now keeps extracted fields open because that is the easiest technical detail for a new user to understand. Heavier sections are collapsed by default:

- anomalies and triggers
- policy evidence
- agent tool trace
- audit metadata

The Evaluation section still shows the KPI cards first. The internal case table is behind a collapsed details control so the page does not feel academic unless someone chooses to inspect it.

## Current Files

- `web/index.html` - contains the hero, upload form, guide cards, Product Path buttons, evidence disclosures, and eval details disclosure.
- `web/styles.css` - positions the aurora canvas, full-width hero layout, compact selected-case state, disclosure styling, sample buttons, and Product Path styling.
- `web/aurora.js` - draws the cursor-reactive aurora line on canvas.
- `web/app.js` - fills guide cards with live case data after a sample or upload run, filters visible review/eval scope to five curated cases, and activates the selected-case layout.

## Verification

- `node --check web/app.js` passed after the latest UI changes.
- `node --check web/aurora.js` passed after the canvas aurora changes.
- The backend health endpoint returned OK during these checks.
- Obsolete docs for the removed workflow-orbit visual and older card experiments were deleted.

## Beginner Test

A beginner should understand the page like this:

1. InvoiceFlow reviews invoice and receivables workflows.
2. AP means vendor invoice review.
3. AR means overdue customer payment follow-up.
4. They can upload a file or click a sample case.
5. Before a case is selected, the cards explain what the system checks.
6. After a case is selected, the decision appears sooner.
7. The Product Path opens evidence, review, and evaluation details.
8. Debug/eval details are available, but hidden until needed.

## Updates

- 2026-07-01 - The visible review queue and eval dashboard now use the same five curated cases as the sample launcher.
- 2026-07-01 - A selected-case state now collapses the intro guide cards, compacts the Product Path, and scrolls to the result after sample/upload completion.
- 2026-07-01 - Evidence and evaluation details now use collapsed sections so the default read stays decision-first.

This is the current source of truth for the top-page UI.
