# Sample Scenario Definitions

This folder will hold the synthetic inputs and expected outputs for the fixed demo cases.

## AP Cases

### ap_001_clean_invoice
- Type: text PDF invoice
- Expected outcome: `approve`
- Notes: complete fields, normal amount, valid terms

### ap_002_missing_po
- Type: invoice missing procurement reference
- Expected outcome: `missing_info`
- Notes: should explicitly ask for missing PO

### ap_003_threshold_review
- Type: invoice above approval threshold
- Expected outcome: `review`
- Notes: should cite approval matrix

### ap_004_duplicate_invoice
- Type: invoice with duplicate identifier
- Expected outcome: `review`
- Notes: should flag duplicate risk

## AR Cases

### ar_001_first_followup
- Type: overdue invoice with no previous reminders
- Expected outcome: standard reminder draft
- Notes: polite and low-escalation tone

### ar_002_escalation_followup
- Type: overdue invoice beyond escalation window
- Expected outcome: escalation-aware follow-up draft
- Notes: should cite escalation policy

### ar_003_payment_claim_no_proof
- Type: customer says payment was sent but no confirmation exists
- Expected outcome: clarification request draft
- Notes: should ask for transaction proof or remittance details
