# Phase 5: Explainability Panel

> Phase 5 made InvoiceFlow's recommendation easier to trust by turning the decision into a visible chain of facts.

---

## In Plain English

Before this phase, the app could recommend an action, show evidence, and expose raw JSON, but a beginner still had to connect too many dots. They could see a recommendation like `missing_info`, but they might not immediately understand whether that meant the invoice was bad, incomplete, or simply waiting for one required field.

Phase 5 added a plain reasoning checklist directly under the main decision. The checklist explains the facts behind the recommendation: whether a PO was required, whether a PO was found, the invoice amount, the approval threshold, the matching policy citation, the risk level, the recommended action, and whether human review is needed.

This is important because finance AI tools need to feel explainable. The user should not feel like the AI is making a mysterious call. They should see the concrete facts that led to the output.

## The Problem It Solves

The product needed a middle layer between a one-sentence summary and a detailed evidence/debug view.

The old flow was roughly:

```text
Recommendation
  |
  v
Evidence tab / raw detail
```

That made the page cleaner than before, but it still required the user to open deeper sections to understand why a recommendation happened.

The new flow is:

```text
Recommendation
  |
  v
Reasoning checklist
  |
  v
Evidence & trace
  |
  v
Advanced debug
```

That is better because it gives a normal user enough context before asking them to inspect technical evidence.

## What We Built

### Step 14: Why This Decision Checklist

Plain English: The result page now explains the recommendation with facts.

The new panel appears under the short “Why this decision?” sentence:

```html
<article class="why-panel" aria-label="Decision reasoning checklist">
  <div>
    <span class="result-label">Reasoning checklist</span>
    <h3>Facts behind the recommendation</h3>
  </div>
  <div id="why-decision-list" class="why-list empty-state">
    Run a workflow to see the policy facts, extracted fields, risk level, and review gate behind the recommendation.
  </div>
</article>
```

Technical detail: The panel uses a stable `why-decision-list` ID so `web/app.js` can populate it after each workflow run. It starts as an empty state and becomes a fact grid once `renderResult(payload)` receives a backend response.

### AP Reasoning Rows

Plain English: For invoice review, the panel focuses on purchase order, amount, policy, risk, action, and review status.

The AP checklist includes:

- PO required?
- PO found?
- Invoice amount
- Matching policy
- Risk level
- Recommended action
- Human review

The app derives those values from existing payload fields:

```javascript
const vendorPolicy = policy.vendor_policy || {};
const poThreshold = vendorPolicy.po_required_above;
const poRequired = poThreshold == null || extraction.amount == null
  ? null
  : Number(extraction.amount) > Number(poThreshold);
```

Technical detail: This avoids backend changes. The frontend already receives `policy_assessment.vendor_policy.po_required_above`, `workflow_result.extraction.amount`, `workflow_result.extraction.po_number`, and decision evidence. Phase 5 simply presents those facts in a more understandable order.

### AR Reasoning Rows

Plain English: For receivables follow-up, the panel explains customer, invoice, due date, escalation, policy, risk, action, and review status.

The AR checklist includes:

- Customer / invoice
- Due date
- Escalation level
- Matching policy
- Risk level
- Recommended action
- Human review

This makes AR cases feel different from AP cases. An AR workflow is not about approving payment. It is about deciding what kind of follow-up email is safe to send.

### Step 15: Safer Action Language

Plain English: The app now separates “ask for more information” from “reject this.”

The recommendation labels changed from raw or ambiguous labels to operator language:

```javascript
const labels = {
  approve: "Approve",
  review: "Human Review",
  reject: "Reject / Do Not Proceed",
  missing_info: "Request Missing Info",
  escalate: "Escalate",
  draft_follow_up: "Draft Follow-Up"
};
```

This matters because `missing_info` should not feel like a failed invoice. It means the operator needs to ask for required details before deciding.

The decision explanation now makes that explicit:

```javascript
if (value === "missing_info") {
  return "Request missing info means the invoice is not being rejected; the safest next step is to ask for the required details before deciding.";
}
```

## How The Pieces Connect

The case summary flow after Phase 5:

```text
Backend workflow payload
        |
        v
renderResult(payload)
        |
        +--> Decision label
        +--> Short reason
        +--> Confidence / risk
        +--> Human review gate
        +--> Evidence count
        +--> Why checklist
```

The key function added in this phase is:

```javascript
renderWhyDecision(whyDecisionList, extraction, policy, finalDecision, evidence, audit, workflow.workflow_type);
```

It decides whether to build AP reasoning rows or AR reasoning rows:

```javascript
const rows = workflowType === "accounts_payable"
  ? buildApWhyRows(extraction, policy, finalDecision, evidence, risk, reviewRequired)
  : buildArWhyRows(extraction, policy, finalDecision, evidence, risk, reviewRequired);
```

This keeps the UI specific to the workflow type without requiring separate pages.

## Common Patterns

### Pattern 1: Explain The Decision With Facts

What it is for: Turn an AI output into a reviewable business decision.

Instead of only showing “Request Missing Info,” the UI now shows the facts behind it:

- PO required: Yes
- PO found: No
- Amount: USD 7800.00
- Matching policy: AP-APPROVAL-001
- Risk: High risk
- Human review: Required

### Pattern 2: Use Business Language Instead Of Backend Codes

What it is for: Make the UI understandable to non-engineers.

The backend can use values like `missing_info`, but the UI should say “Request Missing Info.” The visible page should describe the operator action, not expose internal enum names.

### Pattern 3: Same Component, Different Workflow Rows

What it is for: Keep the UI simple while supporting AP and AR.

The same `why-panel` renders different facts depending on the workflow type. AP shows PO and approval policy. AR shows customer, due date, escalation, and follow-up decision.

## Edge Cases & Gotchas

### 1. Missing info is not rejection

In plain English: A missing PO means “ask for the PO,” not “throw away the invoice.”

Technical cause: The backend recommendation enum has `missing_info`, `review`, and `reject`, but those labels can feel similar unless the UI explains them.

How to avoid: Use operator language and include a meaning sentence for each recommendation.

### 2. AR should not inherit AP language

In plain English: A customer follow-up is not an invoice approval.

Technical cause: AP and AR share the same result surface, but the reasoning fields differ.

How to avoid: Build separate AP and AR reasoning row functions.

### 3. Evidence count is not enough

In plain English: “4 sources” sounds good, but the user needs to know which source mattered.

Technical cause: Counts summarize evidence but do not explain relevance.

How to avoid: Show a matching policy citation in the reasoning checklist and leave fuller evidence details for the Evidence & Reasoning tab.

## Quick Reference

### Files Changed In Phase 5

- `web/index.html`
  - Added the reasoning checklist panel.
  - Replaced raw expected result codes with readable labels.

- `web/app.js`
  - Added `renderWhyDecision`.
  - Added `buildApWhyRows`.
  - Added `buildArWhyRows`.
  - Added `buildRecommendationMeaning`.
  - Clarified recommendation labels and explanations.

- `web/styles.css`
  - Styled the reasoning checklist as a responsive fact grid.

- `steps.md`
  - Logged Steps 14 and 15.

### Phase 5 Commits

- `95887fe add decision reasoning checklist`
- `2d6ac5a docs: log decision reasoning step`
- `6bdbdb3 clarify invoice action labels`
- `0f16451 docs: log action wording step`

### Beginner Test

Can a beginner human understand this page as it goes?

Mostly yes. A beginner can now understand the main decision path because the page explains the recommendation using concrete facts and clearer action labels. The remaining improvement is visual flow: the checklist is understandable, but the page still has several sections below it, so future phases should keep simplifying the evidence and review tabs.

## Updates

- 2026-06-30 - Created after Phase 5 to document the explainability checklist and safer recommendation language.
