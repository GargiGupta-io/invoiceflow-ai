# Phase 8: Product Polish

> Phase 8 made InvoiceFlow feel calmer and more reliable through semantic color polish, clearer error states, and stronger mobile behavior.

---

## In Plain English

Before this phase, InvoiceFlow had the right product flow, explainability, evidence, and signature visual. The remaining issue was polish: badges still felt slightly loud, upload failures were not always clear enough, and mobile layouts needed stronger guardrails.

Phase 8 focused on the parts that make a product feel dependable. Badges now use softer green, amber, red, and blue-gray tones. Upload guidance explains what files work and what to do when OCR is not available. Mobile layouts now stack controls, tabs, cards, and result sections more predictably.

This matters because a finance workflow tool should feel calm and stable. Small UX failures such as unclear upload errors or cramped mobile controls can make the whole project feel unfinished, even when the backend logic is strong.

## The Problem It Solves

The app needed operational polish rather than new features.

The goals were:

```text
calmer colors
clearer failure messages
stable mobile layout
no silent failures
no text overflow
no unnecessary visual noise
```

This phase did not change backend workflow logic. It improved the surface that users judge first.

## What We Built

### Step 20: Badge And Color Polish

Plain English: Status and risk badges now feel softer and more consistent.

The app gained shared semantic color tokens:

```css
--green: #5f8f7c;
--green-soft: rgba(95, 143, 124, 0.16);
--warning: #b98443;
--warning-soft: rgba(222, 184, 124, 0.24);
--danger: #9d463c;
--danger-soft: rgba(190, 103, 93, 0.16);
--info: #5f6f7a;
--info-soft: rgba(95, 111, 122, 0.14);
```

Technical detail: Instead of hardcoding different greens, ambers, and reds across tags, queue statuses, badges, and pills, the UI now uses shared variables. This makes the palette easier to tune and keeps the interface calmer.

### Step 21: Empty And Error States

Plain English: The upload flow now tells the user what went wrong and what to try next.

The page now includes clear upload guidance:

```html
<p class="upload-guidance" id="upload-guidance">
  Supports text-based PDFs, .txt, and .md files. OCR is not configured in this preview, so scanned PDFs may need pasted or text-based input.
</p>
```

The frontend checks supported file types before upload:

```javascript
function isSupportedUploadFile(file) {
  if (!file || !file.name) {
    return false;
  }
  return /\.(pdf|txt|md)$/i.test(file.name);
}
```

It also maps technical failures into user-friendly messages:

```javascript
if (normalized.includes("ocr") || normalized.includes("extractable text") || normalized.includes("pdf_text_extraction_empty")) {
  return "OCR is not configured in this environment. Text-based PDFs and pasted text files still work.";
}
```

Technical detail: This is frontend UX handling. It does not replace backend validation, but it gives the user useful feedback before or after a failed upload.

### Step 22: Mobile Layout

Plain English: The page now stacks cleanly on smaller screens.

The final mobile breakpoint now controls the important layout pieces:

```css
@media (max-width: 980px) {
  .hero-upload {
    grid-template-columns: 1fr;
    width: 100%;
  }

  .entry-board,
  .detail-grid,
  .result-grid,
  .eval-summary-grid,
  .flow-map,
  .decision-summary-card,
  .why-list {
    grid-template-columns: 1fr;
  }
}
```

Technical detail: The CSS file has repeated base rules later in the file, so Step 22 strengthened the final mobile media block to ensure mobile rules win. That was safer than doing a broad CSS refactor in this phase.

## How The Pieces Connect

Phase 8 improves three different product trust signals:

```text
Semantic color
  -> user understands risk/review/safe states faster

Error and empty states
  -> user knows what happened and what to try next

Mobile layout
  -> product does not look broken outside desktop
```

Together, these make the app feel more finished even without adding new workflows.

## Common Patterns

### Pattern 1: Semantic Color Tokens

What it is for: Make status meanings consistent across the app.

Green means safe, amber means review, red means high risk, and blue-gray means neutral information. The same meaning should use the same token everywhere.

### Pattern 2: Friendly Error Translation

What it is for: Convert technical failures into user actions.

Instead of showing only “Upload workflow failed,” the UI says things like:

- choose a supported file
- OCR is not configured
- try a text-based PDF
- run a sample case

### Pattern 3: Final Mobile Override

What it is for: Keep responsive rules reliable even when a CSS file has repeated base sections.

The safest change in this phase was to strengthen the final media block, not reorder the whole stylesheet.

## Edge Cases & Gotchas

### 1. Pastel colors can lose meaning

In plain English: Softer colors should still communicate status.

Technical cause: Low-contrast colors can look pretty but become unclear.

How to avoid: Keep text color distinct and use semantic tokens consistently.

### 2. Upload errors need fallback actions

In plain English: An error message should tell the user what to do next.

Technical cause: Backend exceptions often describe what failed, not how to recover.

How to avoid: Pair every upload failure with a next step such as using a text-based file or running a sample.

### 3. Responsive CSS order matters

In plain English: A mobile rule only works if nothing later overrides it.

Technical cause: CSS applies later matching rules after earlier ones.

How to avoid: Put critical mobile overrides near the end or remove duplicate base rules in a later cleanup.

## Quick Reference

### Files Changed In Phase 8

- `web/styles.css`
  - Added softer semantic color tokens.
  - Applied badge/status/tag color polish.
  - Styled upload guidance.
  - Improved empty-state line height.
  - Strengthened mobile breakpoints.

- `web/index.html`
  - Added upload guidance copy.

- `web/app.js`
  - Added file type validation.
  - Added upload guidance state updates.
  - Added friendly upload error translation.

- `steps.md`
  - Logged Steps 20, 21, and 22.

### Phase 8 Commits

- `736cc48 soften badge colors`
- `bf86bae docs: log badge polish step`
- `2fc681e clarify upload error states`
- `ba500c2 docs: log empty states step`
- `b0bc230 tighten mobile layout`
- `2bf2ef3 docs: log mobile layout step`

### Beginner Test

Can a beginner human understand this page as it goes?

Mostly yes. The page now has clearer status colors, upload guidance, error recovery copy, and better mobile stacking. A beginner can understand what to click, what file types work, what happens during a run, and what to do if upload fails.

## Updates

- 2026-06-30 - Created after Phase 8 to document the badge polish, upload error states, and mobile layout improvements.
