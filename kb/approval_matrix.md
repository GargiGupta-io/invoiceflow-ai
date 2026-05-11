# Approval Matrix

## AP-APPROVAL-001 Standard Thresholds

Use the gross invoice amount in base currency for routing decisions.

| Amount Range | Required Action | Approver |
| --- | --- | --- |
| Up to 5,000 | Auto-approve if all validation checks pass | AP Ops |
| 5,001 to 20,000 | Manual review required | Finance Manager |
| 20,001 to 75,000 | Senior approval required | Head of Finance |
| Above 75,000 | Executive approval required | CFO |

## AP-APPROVAL-002 Purchase Order Policy

- A purchase order is required for all vendor invoices above 3,000.
- If the invoice amount is above 3,000 and the PO number is missing, route the
  case to `missing_info`.
- Services invoices can proceed without a PO only if the vendor is explicitly
  marked as `services-exempt` in the vendor terms document.

## AP-APPROVAL-003 Duplicate Risk Rule

- If the invoice number matches a previously recorded invoice from the same
  vendor, the case should not be approved automatically.
- A duplicate match should be flagged as `review` unless a clear correction note
  is present in the supporting context.

## AP-APPROVAL-004 Terms Mismatch Handling

- If the invoice payment terms differ from the vendor's agreed master terms,
  route the case to `review`.
- If the invoice shortens the agreed payment window without a justification
  note, add a medium-severity anomaly.

## AR-ESCALATION-001 Reminder Cadence

Use the number of overdue days and prior reminders to determine escalation.

| Condition | Escalation Level | Expected Action |
| --- | --- | --- |
| 1 to 7 days overdue, no prior reminder | none | Send first reminder |
| 8 to 21 days overdue or one prior reminder | low | Send second reminder |
| 22 to 45 days overdue or two prior reminders | medium | Escalate tone, request payment timeline |
| More than 45 days overdue or three or more reminders | high | Escalate to finance lead |

## AR-ESCALATION-002 Payment Confirmation Exception

- If the customer claims payment has been made but no remittance proof or bank
  confirmation is attached, do not escalate to collections language.
- Ask for transaction reference, transfer date, and payment confirmation.
