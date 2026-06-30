# Phase 15D: Surface And Motion Polish

> InvoiceFlow now has a more cohesive glass surface system, softer pastel status colors, and smoother motion across the main UI.

---

## In Plain English

The page had the right structure, but some parts still felt like separate pieces. A polished product needs repeated visual rules: similar surfaces, similar hover behavior, similar status colors, and similar spacing.

This phase adds a final visual layer that makes the interface feel more unified. Cards, badges, buttons, tables, and workflow elements now share softer glass surfaces and calmer motion. The green, amber, and red signals are still meaningful, but they are less harsh.

## What Changed

### Softer Color Tokens

Plain English: the status colors now feel calmer and more premium.

The CSS overrides the main semantic colors at the end of the stylesheet:

```css
--green: #5f927f;
--green-soft: rgba(112, 166, 139, 0.18);
--warning: #c58d4f;
--warning-soft: rgba(221, 174, 111, 0.2);
--danger: #b8665d;
--danger-soft: rgba(207, 127, 116, 0.16);
```

These keep the existing palette direction while making the interface less loud.

### Unified Glass Surfaces

Plain English: the main UI pieces now look like they belong to the same product.

The surface layer applies shared border, background, shadow, and blur rules to:

- AP/AR explanation cards
- sample cards
- result cards
- decision and reasoning panels
- evidence/detail columns
- queue and evaluation surfaces
- debug panels

### Motion Polish

Plain English: the interface now responds gently when someone moves around the page.

Hover states now lift cards and buttons slightly. The motion is subtle so it adds polish without distracting from the finance workflow.

## Why This Matters

This phase supports the creative direction without adding heavy 3D or random effects. The UI now has more personality, but it still feels like a serious finance operations console.

## Verification

- The local `/ui` endpoint served successfully.
- Changes were limited to `web/styles.css`.
- Backend, JavaScript behavior, samples, README, and eval logic were not touched.

