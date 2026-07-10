# InvoiceFlow AI Finance Reviewer Demo Pack

This demo pack is a finance-reviewer proof artifact for the hosted
InvoiceFlow AI demo. It explains one AP case and one AR case in business terms
so a finance reviewer can understand what the system checked, why it routed the
case, and what a human should do next.

The data is synthetic and deterministic. It is intended to prove workflow
shape, evidence handling, human review gates, and auditability, not production
finance accuracy on real customer invoices.

## Proof Case 1: Missing PO Invoice

| Field | Value |
| --- | --- |
| Sample ID | `ap_002_missing_po` |
| Workflow | Accounts Payable invoice review |
| Vendor | Quartz Cloud Systems |
| Invoice number | QCS-8842 |
| Amount | USD 7,800.00 |
| Due date | 2026-05-31 |
| Payment terms | Net 30 |
| PO number | Missing |

### Input Invoice Summary

Quartz Cloud Systems submitted invoice `QCS-8842` for USD 7,800.00. The invoice
includes annual observability platform subscription and priority onboarding
support line items. No purchase order number appears in the submitted document.

### Expected Decision

`missing_info`

The case should not be approved yet, and it should not be rejected as invalid.
The correct next action is to request the missing purchase order or send the
case to a finance reviewer before payment continues.

### Extracted Fields

| Field | Extracted value |
| --- | --- |
| Document type | invoice |
| Vendor name | Quartz Cloud Systems |
| Invoice number | QCS-8842 |
| Amount | USD 7,800.00 |
| Due date | 2026-05-31 |
| Payment terms | Net 30 |
| Purchase order | Not found |

### Policy Evidence Used

| Source | Why it matters |
| --- | --- |
| `AP-APPROVAL-002` | Purchase orders are required for vendor invoices above USD 3,000. Missing PO should route to `missing_info`. |
| `AP-POLICY-003` | AP review requires required invoice fields and supporting approval information before payment. |
| `VENDOR-004` | Vendor-specific terms help decide whether the invoice is exempt from the normal PO requirement. |

### Human Review Reason

- Missing purchase order
- Invoice is above the PO threshold
- Manual AP threshold review required before payment

### Audit Trail Summary

1. Invoice text was ingested.
2. Structured fields were extracted.
3. The workflow was routed to Accounts Payable.
4. Policy evidence was retrieved.
5. Validation detected a missing PO on a high-value invoice.
6. The recommendation was set to `missing_info`.
7. Human review was required before payment action.

### Operator Next Step

Ask the vendor or internal requestor for the purchase order number. If the
vendor is claiming exemption, verify that exemption against vendor terms before
approving, rejecting, or returning the case.

## Proof Case 2: AR Payment Claimed, No Proof

| Field | Value |
| --- | --- |
| Sample ID | `ar_003_payment_claim_no_proof` |
| Workflow | Accounts Receivable follow-up |
| Customer | Horizon Health Group |
| Invoice number | AR-6651 |
| Amount | USD 5,400.00 |
| Due date | 2026-04-05 |
| Overdue days | 18 |
| Prior reminders | 1 |

### Expected Decision

Draft a safe follow-up and require human review.

The customer says payment was initiated, but no remittance proof, bank
reference, or transfer date was shared. The system should avoid aggressive
collections language and ask for confirmation details.

### Follow-Up Should Ask For

- transfer date
- transaction reference
- remittance advice

### Policy Evidence Used

| Source | Why it matters |
| --- | --- |
| `AR-ESCALATION-002` | Payment-claimed-without-proof cases should be handled carefully and routed through review. |
| `AR-TEMPLATE-004` | Follow-up language should request payment confirmation details without sounding accusatory. |
| `CUSTOMER-002` | Customer context helps keep escalation level and tone appropriate. |

## Demo Scope

- Guided UI demo: 5 curated cases.
- Backend/evaluation set: 7 synthetic cases.

The UI keeps the guided story focused, while the backend eval set keeps extra
coverage for internal reliability checks.

## Next Validation Step

The strongest next validation step is to replace the bundled synthetic samples
with one company's AP policy rules and 20-30 historical AP/AR cases, then rerun
the same extraction, evidence, decision, review-gate, and audit checks.
