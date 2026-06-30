# Phase 15G: Compact Sample Launcher

> InvoiceFlow now launches demo samples from the compact feature card instead of showing a separate sample grid.

---

## In Plain English

The page had two places for sample demos: a compact “5 curated cases” card and a larger “Run a focused demo case” grid below it. That was redundant and made the page feel heavier than the ReactBits-style reference.

This update removes the separate sample grid and makes the five chips inside the compact card act as the sample launcher. Clicking a case name now runs that sample directly.

## What Changed

### Removed Duplicate Sample Grid

Plain English: the page no longer repeats the same sample choices in a second large section.

`web/index.html` removed the old `sample-board` section. The `Cases` navigation target now points to the compact card section instead.

### Clickable Compact Chips

Plain English: the five case names inside the middle card are now the actual demo buttons.

The existing buttons already had `data-run-sample`, so the app's existing JavaScript automatically picks them up and runs the correct sample:

- Clean Invoice
- Missing PO
- Duplicate Risk
- High-Value
- AR Overdue

### Styling

Plain English: the chips now look and feel clickable.

The CSS adds hover, focus, selected, and running states to the compact sample chips.

## Why This Matters

This makes the page closer to the reference direction: fewer big repeated sections, more compact interactive product cards, and a clearer first screen.

## Verification

- `node --check web/app.js` passed.
- Local `/ui` served successfully.
- Five compact sample buttons remain in the page with `data-run-sample`.
- Backend and JavaScript behavior were not changed.

