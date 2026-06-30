# Phase 15C: Unified Workflow Visual

> InvoiceFlow now has a six-stage visual workflow that connects the product story to the live loading state.

---

## In Plain English

The old visual showed the general idea of the workflow, but it was mostly decorative. It did not clearly show the full product path or react to what the app was doing.

This phase turns the visual into a stronger product signal. The top rail now shows six stages: Invoice, Extract, Policy, Risk, Decision, and Audit. When a workflow runs, the active stage moves forward so the user can see progress through the finance review process.

## What Changed

### Six Stages

Plain English: the workflow visual now tells the whole story in order.

The hero rail now includes:

```text
01 Invoice -> 02 Extract -> 03 Policy -> 04 Risk -> 05 Decision -> 06 Audit
```

This matches the product promise: select or upload a case, extract the facts, check policy, detect risk, recommend an action, and keep an audit trail.

### Active Stage Tracking

Plain English: the visual now reacts while the app is working.

`web/app.js` now tracks the workflow stage with:

```js
function setWorkflowStage(activeIndex) {
  if (!workflowOrbit) {
    return;
  }
  const normalizedIndex = Number.isFinite(activeIndex) ? activeIndex : 0;
  workflowOrbit.dataset.activeStage = String(normalizedIndex);
  for (const node of workflowNodes) {
    const nodeIndex = Number(node.dataset.stageIndex || 0);
    node.classList.toggle("is-active", nodeIndex === normalizedIndex);
    node.classList.toggle("is-complete", nodeIndex < normalizedIndex);
  }
}
```

The loading cue still shows text, but now the visual path also changes state.

### Styling

Plain English: the workflow rail now feels more like one connected system.

The CSS changes:

- uses six stage cells instead of five
- adds numbered labels
- adds active and completed stage styles
- keeps motion subtle and finance-friendly
- uses the existing green and warm palette

## Why This Matters

This is the first creative feature that is also functional. It adds visual personality without becoming a random effect. A recruiter or client can see the workflow path immediately, and the animation reinforces the product logic.

## Verification

- `node --check web/app.js` passed.
- The local `/ui` endpoint served the updated six-stage workflow visual.
- Backend, samples, README, and eval logic were not touched.

