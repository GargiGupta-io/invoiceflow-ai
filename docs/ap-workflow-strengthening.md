# AP Workflow Strengthening

> Accounts Payable strengthening means the system now explains invoice review risks more explicitly instead of returning only a broad recommendation.

---

## In Plain English

This step made the invoice-review side of InvoiceFlow AI more useful for a finance operator. When an invoice has a problem, the system should say exactly what kind of problem it found: a missing purchase order, missing invoice number, duplicate hint, threshold review, policy mismatch, or other AP risk.

Before this step, the AP workflow already had useful checks, but some outputs were hidden behind broader labels. The result could say `missing_info` or `review`, but the AP decision object did not separately carry the missing fields, policy evidence, or human-review requirement.

Now the AP decision is easier to trust and easier to evaluate. The response itself contains the decision, missing fields, evidence used for policy checks, anomalies, human-review status, reviewer summary, and confidence.

## What Changed

The AP workflow now has three clearer layers:

```text
AP extraction
  -> field-specific AP checks
  -> decision payload with review fields
  -> eval assertions that verify those fields
```

That matters because a finance workflow should not treat all failures the same. Missing information is not the same as rejection. A duplicate hint is not the same as a line-item total mismatch. A high-value invoice should go to review even when the invoice is otherwise valid.

## Core AP Checks

The AP assessment now supports these review categories:

- missing vendor name
- missing invoice number
- missing due date
- missing amount
- missing currency
- missing PO number when policy requires it
- duplicate invoice hint
- line-item total mismatch
- payment terms mismatch
- approval threshold exceeded
- vendor policy mismatch reason code
- void, cancelled, or invalid invoice wording

## Output Shape

The AP decision payload now includes:

```text
recommendation
missing_fields
reviewer_summary
evidence
policy_evidence
anomalies
human_review_required
confidence
```

Plain English: the workflow now says what to do, what is missing, what policy supports the decision, what went wrong, whether a person must review it, and how confident the system is.

## Files Updated

### `app/schemas/decision.py`

Plain English: the AP decision contract now has explicit review fields.

Technical detail: `APDecision` now includes `missing_fields`, `policy_evidence`, and `human_review_required`. This makes the backend response more useful to both the UI and eval suite.

### `app/agents/policy.py`

Plain English: missing invoice information is now checked field by field.

Technical detail: `REQUIRED_AP_FIELD_CHECKS` maps each required field to a specific anomaly code and message. This produces clearer anomalies such as `missing_invoice_number` instead of one broad missing-fields bucket.

### `app/agents/decision.py`

Plain English: the AP decision builder now fills the new fields.

Technical detail: `decide_accounts_payable` now derives missing fields, copies selected evidence into `policy_evidence`, and marks `human_review_required` when recommendation, severity, or confidence requires it.

### `app/eval/run_eval.py`

Plain English: the eval suite now checks the new AP output fields.

Technical detail: AP cases can define expected `missing_fields`, `human_review_required`, and `policy_evidence_min`. The evaluator fails a case if those expectations are not met.

### `samples/expected_outputs/ap_*.json`

Plain English: the AP sample expectations now prove that the new output fields are working.

Technical detail: each AP expected-output file now includes the review-field expectations relevant to that case.

### `web/app.js`

Plain English: the UI now shows AP decision missing fields when the decision adds them.

Technical detail: the extracted-fields panel prefers decision-level missing fields when available, which makes missing PO visible even when the extractor itself did not classify it as a missing schema field.

## How The Pieces Connect

```text
sample invoice
  |
  v
ExtractorAgent
  |
  v
assess_accounts_payable()
  |
  v
decide_accounts_payable()
  |
  +--> APDecision.missing_fields
  +--> APDecision.policy_evidence
  +--> APDecision.human_review_required
  +--> APDecision.anomalies
  |
  v
evaluation checks + UI result panel
```

## Why Missing Info Is Separate From Rejection

Plain English: if an invoice is missing a PO, that does not mean the invoice is fake or invalid. It means AP cannot safely continue until the missing information is supplied.

Technically, missing fields resolve to `missing_info`, not `reject`. Invalid invoice language such as void or cancelled still resolves to `reject`.

That distinction makes the workflow feel realistic for finance operations.

## Eval Result

The built-in eval passed after the change:

```text
total cases: 7
passed cases: 7
pass rate: 1.0
workflow match rate: 1.0
extraction field match rate: 1.0
citation check pass rate: 1.0
grounding support pass rate: 1.0
anomaly check pass rate: 1.0
```

Direct AP missing-PO inspection returned:

```text
recommendation: missing_info
missing_fields: ["po_number"]
human_review_required: true
policy_evidence count: 4
anomalies: ["missing_po", "approval_threshold"]
```

## Key Takeaways

- A serious AP workflow needs structured outputs, not only prose.
- Missing information should route to `missing_info`, not `reject`.
- Evidence should travel with the decision payload.
- Human review must be explicit when payment risk exists.
- Eval expectations should check decision shape, not only recommendation labels.

---

*Generated: 2026-05-28 | Project: invoiceflow-ai | Files: app/schemas/decision.py, app/agents/policy.py, app/agents/decision.py, app/eval/run_eval.py, web/app.js*
