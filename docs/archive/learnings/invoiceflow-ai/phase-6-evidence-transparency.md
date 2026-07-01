# Phase 6: Evidence And RAG Transparency

> Phase 6 made policy retrieval visible enough that a user can trace a recommendation back to source evidence.

---

## In Plain English

Before this phase, InvoiceFlow could retrieve policy evidence and show it in the interface, but the evidence still felt a little too much like a technical output. A user could see a policy excerpt and a source ID, but the card did not clearly explain what source it came from, what rule matched, why it mattered, or which part of the decision it influenced.

Phase 6 cleaned that up. The evidence area now reads like a policy match: source, citation, matched rule, policy excerpt, decision impact, and relevance explanation. It also handles weak evidence more safely. If evidence is missing, uncited, or looks like fallback support, the UI tells the operator to send the case to human review instead of acting automatically.

This matters because RAG is only useful in a finance workflow if the user can understand and trust the grounding. The app should never say “AI decided” without showing the policy path behind the recommendation.

## The Problem It Solves

The product needed evidence transparency without forcing the user to understand the term RAG.

The earlier evidence display was useful but generic:

```text
Policy match
Source title
Citation id
Excerpt
Used for
Why relevant
```

The improved evidence display is more explicit:

```text
Source: Approval Matrix
Citation: AP-APPROVAL-002
Matched rule: Purchase Order Policy
Excerpt: A purchase order is required...
Decision impact: PO and approval requirement check
Why relevant: Matches query terms...
```

That is easier for a beginner because it answers what the evidence is and why the system cared about it.

## What We Built

### Step 16: Clean Policy Evidence Panel

Plain English: Evidence cards now look like policy matches instead of raw retrieval cards.

The evidence column was renamed:

```html
<h3>Policy evidence</h3>
```

The renderer now builds a clearer evidence card:

```javascript
source.textContent = `Source: ${extractEvidenceSourceName(item)}`;
citation.textContent = `Citation: ${item.source_id || "uncited"}`;
title.textContent = extractEvidenceRuleName(item);
appendEvidenceDetail(detailList, "Decision impact", inferEvidenceInfluence(item));
appendEvidenceDetail(detailList, "Why relevant", item.relevance_reason || "Supports this workflow decision.");
```

Technical detail: The backend already returns `source_title`, `source_id`, `excerpt`, and `relevance_reason`. The frontend now splits `source_title` into a source name and rule name when the title follows the pattern `Source - Rule`.

Example:

```text
Approval Matrix - AP-APPROVAL-002 Purchase Order Policy
```

becomes:

```text
Source: Approval Matrix
Matched rule: AP-APPROVAL-002 Purchase Order Policy
```

### Step 17: Weak Evidence Behavior

Plain English: If the app does not have good supporting evidence, it tells the user to review instead of acting automatically.

The UI now checks whether evidence is weak:

```javascript
function isEvidenceWeak(evidence) {
  if (!Array.isArray(evidence) || evidence.length === 0) {
    return true;
  }
  return evidence.some((item) => {
    const sourceId = String(item.source_id || "").trim().toLowerCase();
    const reason = String(item.relevance_reason || "").trim().toLowerCase();
    return !sourceId || sourceId === "uncited" || sourceId === "fallback" || reason.includes("fallback");
  });
}
```

Technical detail: This is a frontend safety signal. It does not change backend decisions. It changes the visible behavior so the product does not overstate confidence when grounding is absent or weak.

The decision summary now uses that weak-evidence signal:

```javascript
const weakEvidence = isEvidenceWeak(evidence);
const effectiveReviewRequired = reviewRequired || weakEvidence;
```

If evidence is weak, the review card says:

```text
Required: policy evidence is missing or too weak for an automatic decision.
```

The evidence summary says:

```text
Weak or missing evidence. Route to human review before acting.
```

## How The Pieces Connect

The evidence flow now works like this:

```text
Backend retrieves policy chunks
        |
        v
Decision includes evidence payloads
        |
        v
Frontend renders policy evidence cards
        |
        +--> Strong evidence: show source, citation, rule, excerpt, impact
        |
        +--> Weak evidence: require human review visibly
```

That flow makes RAG understandable without using jargon on the main page.

## Common Patterns

### Pattern 1: Evidence Cards Need Purpose

What it is for: Show the user not just what source matched, but why it matters.

An evidence card should answer:

- Where did this come from?
- What citation identifies it?
- What rule matched?
- What did the rule say?
- What decision did it influence?
- Why was it relevant?

### Pattern 2: Weak Evidence Should Lower Autonomy

What it is for: Prevent ungrounded AI from sounding too confident.

If evidence is missing, uncited, or fallback-based, the UI should not present the result as a normal supported decision. It should route the case to human review.

### Pattern 3: RAG Without Saying RAG

What it is for: Make retrieval useful to non-technical users.

Recruiters and engineers can recognize this as RAG transparency, but a finance operator only needs to see “Policy evidence” and “Citation.” That is the right abstraction for the product.

## Edge Cases & Gotchas

### 1. Evidence count can be misleading

In plain English: Four weak sources are not better than one strong citation.

Technical cause: Counting evidence does not tell whether it is relevant or grounded.

How to avoid: Show source, citation, rule, and relevance reason. Detect weak/fallback evidence separately.

### 2. Fallback evidence must not sound authoritative

In plain English: If the app had to fall back because it could not find policy, the operator should know.

Technical cause: Some systems create fallback context when retrieval fails.

How to avoid: Treat fallback relevance as weak and route to review visibly.

### 3. Retrieval explanations should be short

In plain English: A user needs the policy trail, not a lecture on vector search.

Technical cause: RAG systems can expose too many internals.

How to avoid: Keep details compact: source, citation, rule, excerpt, impact, relevance.

## Quick Reference

### Files Changed In Phase 6

- `web/index.html`
  - Renamed the evidence column to Policy evidence.

- `web/app.js`
  - Improved evidence rendering.
  - Added source/rule extraction helpers.
  - Added weak evidence detection.
  - Routed weak evidence to visible human review behavior.

- `web/styles.css`
  - Improved evidence chips and excerpt styling.

- `steps.md`
  - Logged Steps 16 and 17.

### Phase 6 Commits

- `4483d4d clean policy evidence cards`
- `883d8c1 docs: log policy evidence step`
- `fe70dd2 route weak evidence to review`
- `7e6e0cd docs: log weak evidence step`

### Beginner Test

Can a beginner human understand this page as it goes?

Mostly yes. The evidence panel now explains the policy source, citation, matched rule, reason, and decision impact. A beginner still may not understand every policy term, but they can trace the decision back to a source and see when weak evidence requires review.

## Updates

- 2026-06-30 - Created after Phase 6 to document the policy evidence card cleanup and weak evidence routing behavior.
