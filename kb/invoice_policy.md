# Invoice Processing Policy

## AP-POLICY-001 Required Fields

An invoice should be treated as incomplete if any of the following are missing:

- vendor name
- invoice number
- invoice amount
- currency
- due date

Missing required fields should produce a `missing_info` recommendation unless
the missing field can be recovered from trusted case context.

## AP-POLICY-002 Extraction Expectations

- Structured outputs must normalize currency codes to ISO-style short forms such
  as `USD`, `EUR`, `INR`, `SGD`, and `GBP`.
- Dates should be captured in `YYYY-MM-DD` format when possible.
- If OCR or parsing quality is low, record that in the extraction warnings
  instead of silently guessing.

## AP-POLICY-003 Validation Checks

Each invoice review should evaluate:

1. whether the invoice has all required fields
2. whether the PO requirement applies and is satisfied
3. whether payment terms match vendor master terms
4. whether the invoice appears to be a duplicate
5. whether the amount crosses an approval threshold

## AP-POLICY-004 Recommendation Meanings

- `approve`: validation checks passed and the case fits policy for approval
- `review`: the case has a policy conflict, duplicate risk, or threshold-based
  manual approval requirement
- `reject`: the invoice is clearly invalid or unsupported
- `missing_info`: the invoice lacks information needed for a policy decision

## AP-POLICY-005 Reviewer Summary

The reviewer summary should be concise and operational. It should mention:

- the top decision reason
- the highest-severity anomaly if one exists
- the next action for the finance team

## AR-POLICY-001 Follow-Up Rules

Overdue follow-up drafts must:

- stay professional and non-hostile
- mention invoice number, amount, and due date when available
- ask for a payment timeline or payment confirmation
- avoid threatening language unless the escalation level is high

## AR-POLICY-002 Grounding Requirement

Any follow-up or recommendation should be grounded in:

- extracted invoice/case details
- at least one policy or reminder rule
- cited evidence from the retrieved context
