# Knowledge Base

This folder contains the synthetic finance documents that the retrieval layer
will search against.

The demo uses these sources to ground two workflows:

- `accounts_payable`: invoice review, approval routing, missing-info handling
- `accounts_receivable`: overdue follow-up drafting and escalation guidance

Each file is intentionally small, structured, and citeable. The later retrieval
step should return:

- the source file name
- the relevant section heading
- the short excerpt used as evidence

## Source Files

- `approval_matrix.md`: approval thresholds and routing rules
- `invoice_policy.md`: validation and processing rules for AP invoices
- `reminder_templates.md`: AR reminder cadence, escalation guidance, and tone
- `vendor_terms.md`: synthetic vendor master data and payment expectations

## Design Notes

- These are synthetic documents built for the demo only.
- Retrieval should prefer the smallest relevant excerpt instead of full files.
- Final decisions should cite at least one policy source and one case-specific
  source when available.
