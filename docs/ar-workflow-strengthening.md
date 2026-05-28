# AR Workflow Strengthening

> Accounts Receivable strengthening means the system now explains follow-up drafts, escalation reasons, and human-review gates more explicitly.

---

## In Plain English

This step made the receivables side of InvoiceFlow AI more useful for a finance operator. Instead of only producing a subject line and an email draft, the AR workflow now says why a follow-up is gentle, stronger, or review-worthy.

The key distinction is safety. A first reminder can be sent without much risk. A payment claim without proof should be handled carefully because the customer says they paid, but the finance team cannot reconcile it yet. A more overdue account with prior reminders needs a firmer tone and a human review gate.

The output now makes those differences visible in both the backend payload and the eval suite.

## What Changed

The AR decision payload now includes:

```text
escalation_level
subject
follow_up_email
tts_safe_subject
tts_safe_follow_up
followup_subject
followup_draft
followup_subject_tts
followup_draft_tts
evidence
trigger_codes
customer_tone
human_review_required
confidence
```

The older `followup_*` fields remain for compatibility. The clearer `subject`, `follow_up_email`, and TTS-safe fields make the API easier to understand.

## Core AR Checks

The AR workflow now tracks:

- overdue days
- prior reminders
- customer tone
- payment claimed without proof
- missing invoice number
- missing due date
- escalation threshold
- dispute or reconciliation-risk language

## Files Updated

### `app/schemas/decision.py`

Plain English: the AR response now has clear names for the customer-facing draft and review state.

Technical detail: `ARDecision` now carries `subject`, `follow_up_email`, `tts_safe_subject`, `tts_safe_follow_up`, `trigger_codes`, `customer_tone`, and `human_review_required`.

### `app/agents/policy.py`

Plain English: the AR assessment now records why a case is risky or safe.

Technical detail: `ARWorkflowAssessment` now stores customer tone and dispute-language state. Trigger codes now include tone, overdue severity, reminder count, payment-claim risk, and escalation level.

### `app/agents/editor.py`

Plain English: the AR draft builder now fills both the old and new output fields.

Technical detail: `draft_accounts_receivable` now returns the richer AR schema and marks human review when confidence is low, payment proof is missing, dispute language is present, escalation is medium/high, or required fields are missing.

### `app/orchestrator/agent_trace.py`

Plain English: the audit trail now agrees with the decision payload about whether a person should review the output.

Technical detail: `build_human_review_gate` reads `decision.human_review_required` when present, then uses that value for the gate.

### `app/eval/run_eval.py`

Plain English: the eval suite now checks AR reliability beyond just the email text.

Technical detail: AR expected outputs can now verify review status, subject/body fields, TTS-safe fields, and required trigger codes.

### `samples/expected_outputs/ar_*.json`

Plain English: each AR demo case now proves a different behavior.

The first follow-up remains review-free. The escalation case requires review. The payment-claim case requires review and asks for transfer date, transaction reference, and remittance proof.

### `web/app.js`

Plain English: the UI now reads the richer AR subject and review state.

Technical detail: the decision summary prefers `subject` and `human_review_required` from the decision payload when available.

## How The Pieces Connect

```text
AR email or payment-claim sample
  |
  v
ExtractorAgent
  |
  v
assess_accounts_receivable()
  |
  +--> overdue_days
  +--> prior_reminders
  +--> payment_claim
  +--> customer_tone
  +--> dispute_language
  +--> trigger_codes
  |
  v
draft_accounts_receivable()
  |
  +--> subject
  +--> follow_up_email
  +--> tts_safe_subject
  +--> tts_safe_follow_up
  +--> human_review_required
  |
  v
eval checks + UI result card
```

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
subject check pass rate: 1.0
mention check pass rate: 1.0
```

Direct AR inspection showed:

```text
ar_001_first_followup: escalation none, human_review_required false
ar_002_escalation_followup: escalation medium, human_review_required true
ar_003_payment_claim_no_proof: escalation low, human_review_required true
```

## Key Takeaways

- AR output should be useful without raw JSON.
- Payment-claimed-without-proof is not just a normal reminder; it needs careful reconciliation language.
- Human review should be explicit before customer-facing outreach when risk is present.
- Eval checks should inspect trigger reasons, not only final email wording.

---

*Generated: 2026-05-28 | Project: invoiceflow-ai | Files: app/schemas/decision.py, app/agents/policy.py, app/agents/editor.py, app/orchestrator/agent_trace.py, app/eval/run_eval.py, web/app.js*
