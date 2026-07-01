# Phase 15B: Page Copy Organization

> InvoiceFlow now groups explanatory text into clearer product sections so the page feels intentional instead of sentence-heavy.

---

## In Plain English

The page already had the right ideas, but too many sentences were sitting separately. That makes a first-time viewer work too hard because they have to decide which line matters first.

This phase reorganized the copy into smaller, labeled groups. AP and AR are now explained as two finance desks. The start area now clearly says what the user should do. The product path now appears as a simple line of steps: select/upload, extract facts, check policy, detect risk, recommend action, and save the audit trail.

## What Changed

### AP/AR Explanation

Plain English: the finance terms are now explained where the user first sees the product.

`web/index.html` changed the old paragraph into two compact cards:

- AP desk: Accounts Payable
- AR desk: Accounts Receivable

This is easier for a beginner because they do not need to already know finance terminology.

### Intake Copy

Plain English: the upload area now has a clearer instruction before the controls.

The text now says:

- Start the review
- Upload a document with AP/AR selected, or run a polished sample case below.

This makes the first action clearer without turning the top of the page into a long explanation.

### Product Path

Plain English: the page now shows the order of the product experience.

The new path line is:

```text
Select or upload -> Extract facts -> Check policy -> Detect risk -> Recommend action -> Save audit trail
```

This helps the page feel like one guided workflow instead of separate blocks.

## Why This Matters

ReactBits works well because even when there is a lot of text, the text is arranged in clear clusters with strong rhythm. This phase applies that idea to InvoiceFlow without copying the visual design directly.

The goal is not to remove every sentence. The goal is to make each sentence belong to a clear section so the viewer can understand the product step by step.

## Verification

- The local `/ui` endpoint served the updated copy.
- Changes were limited to frontend markup and styles.
- Backend, samples, eval logic, and README were not touched.

