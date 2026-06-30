# Phase 15I: Hero Sample Control Cleanup

> InvoiceFlow now uses the compact sample card as the sample launcher instead of showing extra AP/AR sample buttons under the upload area.

---

## In Plain English

The hero area had too many controls. It showed the upload form, hidden workflow status pills, two large AP/AR sample buttons, and then the compact sample card below. That made the top of the page feel busy.

This update removes the visible extra sample buttons and makes the compact sample card clearer. The middle card now says “Run sample,” and the five cases are stacked one below another so the user understands they are clickable options.

## What Changed

### Removed Visible Hero Sample Buttons

Plain English: the big “Run AP Sample” and “Run AR Sample” buttons are gone.

The status row is kept in the DOM but hidden so the JavaScript can still update the status nodes safely.

### Added Run Sample Label

Plain English: the sample card now tells the user what to do.

The compact sample card now has a `Run sample` label above the five case buttons.

### Stacked Sample Buttons

Plain English: all five cases now line up vertically.

The buttons no longer shift into uneven side-by-side placement. This makes the card easier to scan and closer to the reference direction.

## Verification

- `node --check web/app.js` passed.
- The compact sample buttons still use `data-run-sample`, so the existing JavaScript continues to run samples automatically.
- Backend and workflow logic were not changed.

