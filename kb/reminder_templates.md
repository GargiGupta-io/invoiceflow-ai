# Reminder Templates And Escalation Guidance

## AR-TEMPLATE-001 First Reminder

Use for low-friction cases that are only slightly overdue.

Subject pattern:
`Friendly reminder: invoice {invoice_number} was due on {due_date}`

Tone guidance:

- assume good intent
- keep the message short
- ask whether payment has already been initiated

Suggested body pattern:

> Hello {customer_name},  
> This is a quick reminder that invoice {invoice_number} for {amount}
> was due on {due_date}. If payment has already been initiated, please share
> the transfer details. Otherwise, could you let us know the expected payment
> date?

## AR-TEMPLATE-002 Second Reminder

Use when the invoice is materially overdue or one reminder has already been sent.

Subject pattern:
`Second reminder: invoice {invoice_number} remains unpaid`

Tone guidance:

- stay polite but more direct
- ask for a firm timeline
- mention previous follow-up where relevant

## AR-TEMPLATE-003 Escalated Follow-Up

Use for medium or high escalation cases.

Subject pattern:
`Action requested: overdue invoice {invoice_number}`

Tone guidance:

- state overdue status clearly
- ask for immediate confirmation or a payment plan
- mention escalation to finance stakeholders when required

## AR-TEMPLATE-004 Payment Claim Without Proof

If a customer says payment has already been made but there is no confirmation:

- acknowledge the update
- ask for bank reference, transfer date, and remittance proof
- avoid accusing the customer of non-payment

Suggested body pattern:

> Hello {customer_name},  
> Thanks for the update. We have not yet been able to match the payment for
> invoice {invoice_number} in our records. Could you please share the transfer
> date, transaction reference, and remittance advice so we can reconcile it?

## AR-TEMPLATE-005 Escalation Notes

- `none`: first reminder language only
- `low`: second reminder language, still collaborative
- `medium`: request explicit timeline and mention internal follow-up
- `high`: escalate to finance lead and ask for urgent resolution
