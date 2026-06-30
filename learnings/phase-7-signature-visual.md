# Phase 7: Signature Creative Visual

> Phase 7 added a restrained visual identity cue that explains the workflow without turning the finance tool into a flashy animation demo.

---

## In Plain English

Before this phase, InvoiceFlow had become clearer as a product, but the top of the page still lacked a memorable visual moment. The user could read the product promise, but there was no quick visual signal showing how the product actually works.

Phase 7 added one simple workflow visual near the top: Invoice → Extract → Policy Check → Decision → Audit. It also added subtle motion while a workflow is running. The motion is tied to real processing states, so it helps the user understand that work is happening rather than decorating the page randomly.

This matters because the app should show creative frontend taste without losing its serious finance-operations feel. The visual should help the product story, not compete with it.

## The Problem It Solves

The page needed creative polish, but not a heavy 3D or effects-heavy landing page.

The design target was:

```text
simple product flow
subtle motion
finance-friendly colors
no distracting animation
no huge marketing hero
```

The chosen visual is intentionally small and tied to the actual workflow. It reinforces the paid-ready promise:

```text
Select/upload case
  -> extract facts
  -> check policy
  -> recommend action
  -> preserve audit trail
```

## What We Built

### Step 18: Workflow Visual

Plain English: The hero now shows the core workflow in one glance.

The HTML added this block:

```html
<div class="workflow-orbit" aria-label="InvoiceFlow workflow path">
  <span class="workflow-node">Invoice</span>
  <span class="workflow-node">Extract</span>
  <span class="workflow-node">Policy Check</span>
  <span class="workflow-node">Decision</span>
  <span class="workflow-node">Audit</span>
</div>
```

Technical detail: This is a simple semantic HTML/CSS visual. It does not need canvas, Three.js, or an extra frontend framework. That was the right tradeoff because the app is currently a static frontend served by FastAPI, and the visual needs to stay lightweight and reliable.

### Step 19: Subtle Motion

Plain English: The workflow visual and status pills now react when work is actually running.

The JavaScript toggles a page-level state:

```javascript
document.body.classList.add("workflow-running");
```

and removes it when the run finishes:

```javascript
document.body.classList.remove("workflow-running");
```

Technical detail: This keeps the animation logic in CSS. JavaScript only tells the page whether the workflow is running. CSS decides how that state looks.

The running state speeds up the workflow sweep and gives nodes a soft pulse:

```css
body.workflow-running .workflow-orbit::after {
  animation-duration: 2.6s;
}

body.workflow-running .workflow-node {
  animation: nodeBreathe 2.4s infinite ease-in-out;
}
```

The status pill also gets a small running indicator:

```css
.status-pill.running::before {
  content: "";
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: currentColor;
  opacity: 0.55;
  animation: statusBlink 1.15s infinite ease-in-out;
}
```

## How The Pieces Connect

The visual behavior is connected to the workflow run lifecycle:

```text
User runs sample/upload
        |
        v
showLoadingCue()
        |
        +--> body gets workflow-running class
        +--> workflow nodes pulse
        +--> status pill blinks
        |
        v
workflow completes/fails
        |
        v
hideLoadingCue()
        |
        +--> body loses workflow-running class
        +--> motion stops
```

This keeps motion meaningful. It appears when the system is doing work and stops when the work is done.

## Common Patterns

### Pattern 1: State-Driven Motion

What it is for: Animate only when the product state calls for it.

The app uses a body class instead of always-on animation everywhere. This is cleaner because the motion communicates processing.

### Pattern 2: Lightweight Visual Identity

What it is for: Add personality without increasing technical risk.

The workflow visual uses HTML and CSS. It loads instantly, is easy to maintain, and does not introduce a dependency.

### Pattern 3: Reduced-Motion Safety

What it is for: Respect users who prefer less animation.

The CSS includes:

```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.001ms !important;
    animation-iteration-count: 1 !important;
    scroll-behavior: auto !important;
  }
}
```

This is important because motion should never make the app uncomfortable or harder to use.

## Edge Cases & Gotchas

### 1. Motion can make finance apps feel unserious

In plain English: Too much animation makes a workflow tool look like a toy.

Technical cause: Decorative effects compete with operational content.

How to avoid: Tie motion to workflow state and keep movement subtle.

### 2. Visuals must survive mobile

In plain English: A horizontal five-step visual can become unreadable on a phone.

Technical cause: Fixed horizontal layouts squeeze text.

How to avoid: The workflow visual stacks vertically under the existing responsive breakpoint.

### 3. Animation should be CSS-led

In plain English: JavaScript should not micromanage every animation frame.

Technical cause: Animation logic in JS is harder to maintain and can cause performance issues.

How to avoid: Use JS for state, CSS for presentation.

## Quick Reference

### Files Changed In Phase 7

- `web/index.html`
  - Added the top workflow visual.

- `web/app.js`
  - Added `workflow-running` body state during loading.

- `web/styles.css`
  - Styled the workflow path.
  - Added workflow sweep animation.
  - Added node pulse animation during runs.
  - Added running status dot animation.
  - Added reduced-motion safeguards.

- `steps.md`
  - Logged Steps 18 and 19.

### Phase 7 Commits

- `d5b5680 add workflow path visual`
- `d223085 docs: log workflow visual step`
- `e84c8fe add subtle workflow motion`
- `ef53128 docs: log motion polish step`

### Beginner Test

Can a beginner human understand this page as it goes?

Yes for the top workflow story. The visual makes the product path clearer before the user reaches the upload controls: invoice, extraction, policy check, decision, audit. The rest of the page still has deeper sections, but the first impression now explains the core workflow faster.

## Updates

- 2026-06-30 - Created after Phase 7 to document the workflow visual and state-driven motion polish.
