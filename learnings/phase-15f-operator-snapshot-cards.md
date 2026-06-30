# Phase 15F: Operator Snapshot Cards

> The operator snapshot section now uses ReactBits-inspired feature cards instead of plain dashboard boxes.

---

## In Plain English

The user compared the current InvoiceFlow section with the ReactBits “What's inside” cards. The issue was not just color or spacing. The InvoiceFlow cards were plain summary boxes, while ReactBits uses cards with a visual preview area and a copy area.

This update restructures the three cards under the upload controls so each card has a top visual zone and a bottom explanation zone. That makes the section feel more designed and less like a basic dashboard.

## What Changed

### Card Structure

Plain English: each card now has a picture-like area at the top and the explanation below it.

`web/index.html` now wraps each entry card in:

- `.entry-visual`
- `.entry-copy`

The existing dynamic IDs are preserved:

- `entry-workflow-state`
- `entry-workflow-detail`
- `entry-sample-count`
- `entry-audit-state`
- `entry-audit-detail`

That means the backend-driven UI updates still work.

### Visual Preview Areas

Plain English: each card now previews what it represents.

The three previews are:

- Workflow State: small abstract workflow panels
- Sample Cases: clickable sample chips in a preview field
- Latest Audit: small audit/status circles

### Styling

Plain English: the section now feels closer to the ReactBits reference.

The CSS adds:

- larger card proportions
- a staggered middle card
- preview/copy separation
- soft line-art style visuals
- responsive single-column stacking

## Why This Matters

This is the type of visual polish that makes the page feel more portfolio-ready. It still does not overload the app with heavy 3D, but it shows creative frontend taste through layout, rhythm, and visual hierarchy.

## Verification

- Local `/ui` served the updated markup successfully.
- Existing dynamic IDs were preserved.
- Backend and JavaScript behavior were not changed.

