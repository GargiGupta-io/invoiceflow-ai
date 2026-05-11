# Peakflo Finance Agent Demo

A focused finance workflow AI demo built to show OCR-assisted extraction, retrieval-grounded reasoning, agent-style orchestration, and Python backend engineering in a form that closely matches the Peakflo ML Engineer Intern role.

## Status

Scaffolded. Core workflows, schemas, knowledge-base docs, sample data, document
ingestion, and structured extraction are in place. Validation/retry is now
implemented, with retrieval and routing still pending.

## Goal

Build a small but credible workflow system that can:
- ingest an invoice PDF or finance-related email
- extract structured fields
- retrieve policy and approval context
- route the case into AP or AR workflow
- return a grounded recommendation or follow-up draft

## Target Workflows

### Accounts Payable
- invoice ingestion
- structured extraction
- policy retrieval
- approval / review / reject recommendation

### Accounts Receivable
- overdue invoice context review
- reminder and escalation retrieval
- grounded follow-up email drafting

## Locked Workflow Scope

This project supports exactly two business flows:

### Flow A: AP Invoice Review

Input:
- invoice PDF or scanned invoice
- optional vendor context

Output:
- extracted structured invoice fields
- detected anomalies
- approval recommendation: `approve`, `review`, `reject`, or `missing_info`
- cited policy evidence
- short reviewer summary

Core checks:
- missing purchase order
- amount above approval threshold
- duplicate invoice identifier
- payment terms mismatch
- incomplete vendor details

### Flow B: AR Overdue Follow-Up

Input:
- overdue invoice record or customer finance email
- reminder history and escalation rules

Output:
- extracted case context
- follow-up status assessment
- recommended escalation level
- grounded follow-up email draft
- cited policy evidence

Core checks:
- invoice age vs reminder policy
- previous reminder count
- escalation threshold crossed
- missing payment confirmation

## Demo Scenarios

The demo should focus on a small fixed set of believable cases instead of open-ended chat.

### AP Scenarios

1. Clean invoice under threshold
- expected result: `approve`
- reason: fields complete, no policy conflicts

2. Invoice missing PO number
- expected result: `missing_info`
- reason: required procurement reference absent

3. Invoice above manual approval threshold
- expected result: `review`
- reason: amount triggers extra approval step

4. Duplicate invoice number
- expected result: `review`
- reason: possible duplicate payment risk

### AR Scenarios

5. First overdue reminder
- expected result: polite follow-up email
- reason: overdue but not yet escalated

6. Repeated overdue case past escalation window
- expected result: stronger escalation-aware follow-up
- reason: reminder threshold exceeded

7. Customer claims payment sent but no confirmation exists
- expected result: evidence-seeking follow-up
- reason: ambiguous payment status

## Planned Architecture

```text
[PDF / Email Input]
        |
        v
[Ingestion Layer]
        |
        v
[Extractor Agent] ---> structured JSON
        |
        v
[Router: AP or AR]
        |
        +-------------------+
        |                   |
        v                   v
[Research/Policy]      [Research/Policy]
        |                   |
        v                   v
[Decision Agent]       [Editor Agent]
        |                   |
        +---------+---------+
                  |
                  v
      [Validated response + evidence]
```

## Repository Layout

```text
peakflo-finance-agent-demo/
|- api/
|- app/
|  |- schemas/
|  |- ingest/
|  |- rag/
|  |- agents/
|  |- orchestrator/
|  |- prompts/
|  `- eval/
|- kb/
|- samples/
|  |- invoices/
|  |- emails/
|  `- expected_outputs/
|- web/
|- tests/
|- .env.example
|- .gitignore
|- README.md
`- requirements.txt
```

## Planned Tech Stack

- Python
- FastAPI
- Pydantic
- ChromaDB
- OpenAI-compatible LLM API
- PDF/OCR ingestion
- Minimal web UI

## Step 1 Output

This initial scaffold includes:
- repository structure
- environment template
- dependency baseline
- initial README

## Next Steps

1. Chunk and index the finance knowledge base
2. Add retrieval with source citations
3. Add routing and decision workflows
