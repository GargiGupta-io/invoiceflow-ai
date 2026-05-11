# Peakflo Finance Agent Demo Plan

Last updated: May 10, 2026

## Progress

- Step 1 complete: repo skeleton, `.env.example`, `requirements.txt`, `.gitignore`, and baseline `README.md` created.

## Goal

Build a small finance workflow AI system that strongly matches the Peakflo ML Engineer Intern role by demonstrating:
- OCR / document ingestion
- structured extraction
- retrieval grounding
- agentic workflow orchestration
- Python backend engineering
- evaluation and reliability thinking

## Why This Project

Peakflo is hiring around:
- agentic AI workflows
- prompt refinement
- RAG / retrieval grounding
- OCR and structured finance extraction
- finance-specific automation
- strong Python backend development

This project is meant to show a compact but believable version of that.

## Recommended Scope

Project name:
- `peakflo-finance-agent-demo`

Core workflow:
1. Upload an invoice PDF or finance-related email
2. Extract structured fields
3. Retrieve policy / approval / vendor context
4. Route the case into AP or AR flow
5. Return recommendation, evidence, and a drafted action

Primary use cases:
- AP approval recommendation
- AR overdue follow-up drafting

## Progress

- Step 1 complete: repo skeleton, `.env.example`, `requirements.txt`, `.gitignore`, and baseline `README.md` created.
- Step 2 complete: exact AP and AR workflows plus fixed demo scenarios defined in `README.md` and `samples/README.md`.
- Step 3 complete: strict Pydantic schemas created for extraction, evidence, anomaly flags, AP decisions, AR decisions, and final workflow results.
- Step 4 complete: synthetic finance knowledge-base files created for approval rules, invoice policy, reminder guidance, and vendor/customer terms.
- Step 5 complete: sample AP invoices, AR cases, and expected JSON output targets created under `samples/`.
- Step 6 complete: document ingestion added for PDF and text-based fixtures through `app/ingest/pdf_reader.py`.
- Step 7 complete: OCR fallback added for scanned or image-based PDF pages through `app/ingest/ocr.py`.
- Step 8 complete: extractor agent added with a strict schema-aligned output path, heuristic development mode, and LLM-ready prompt.
- Step 9 complete: schema validation retry path added for extraction, including local repair and LLM repair prompt flow.
- Step 10 complete: KB markdown files now chunk into citeable sections and build into a deterministic lexical index for retrieval.
- Step 11 complete: retrieval added on top of the KB index, with ranked citeable hits and evidence payload conversion for downstream decisions.
- Step 12 complete: deterministic workflow routing added so extracted cases resolve into AP or AR before decision logic runs.
- Step 13 complete: grounded policy-context assembly added so decision layers receive route-aware evidence bundles instead of raw retrieval hits.
- Step 14 complete: AP decision logic added for approve, review, and missing-info outcomes, including anomaly flags and reviewer summaries.
- Step 15 complete: AR drafting flow added for reminder, escalation, and payment-confirmation follow-up cases.
- Step 16 complete: shared workflow policy assessment added for AP anomalies, line-item amount mismatch, and AR escalation triggers.
- Step 17 complete: full extraction, routing, retrieval, and decision flow wired behind FastAPI sample and upload endpoints.
- Step 18 complete: evaluation dataset and eval runner added for extraction checks, decision checks, citation coverage, and latency scoring.
- Step 19 complete: minimal operator UI added for running sample/upload workflows and inspecting route, decision, anomaly, evidence, and raw JSON output.
- Step 20 complete: README rewritten with architecture, workflow, setup, UI/API usage, evaluation, limitations, and demo instructions.
- Step 21 complete: showcase assets added for a 60-90 second demo, resume bullets, and application-ready project summary.
- Step 22 complete: TTS-safe AR subject and follow-up output added for readable dates, amounts, and identifiers.

## Success Criteria

- Looks like a real workflow system, not a generic chatbot
- Uses Python and FastAPI
- Produces structured output
- Shows grounding and evidence
- Includes evaluation and reliability thinking
- Can be demoed in under 90 seconds

## Architecture

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

## Phases

### Phase 1: Project Framing And Contracts

1. Create the repo skeleton, environment file, and baseline README
2. Define the exact two use cases: AP approval recommendation and AR follow-up drafting
3. Define strict Pydantic schemas for extraction, retrieval evidence, and decision outputs
4. Create a small synthetic knowledge base for policy, approval rules, and reminder guidance
5. Create synthetic sample inputs and expected outputs

### Phase 2: Ingestion And Structured Extraction

6. Build PDF text extraction and email text ingestion [done]
7. Add OCR fallback for scanned invoices [done]
8. Implement the extractor agent that converts raw content into strict JSON [done]
9. Add validation and retry behavior when extraction output fails schema checks [done]

### Phase 3: Retrieval And Case Routing

10. Chunk and index the finance knowledge base [done]
11. Implement retrieval with scored evidence and source references [done]
12. Build a router that classifies cases into AP or AR workflows [done]
13. Add policy assembly logic so the downstream decision is always grounded in retrieved context [done]

### Phase 4: Agent Workflow And Business Actions

14. Build the AP decision flow for approve / review / reject / missing-info recommendations [done]
15. Build the AR drafting flow for overdue follow-up emails [done]
16. Add anomaly flags such as missing PO, amount mismatch, duplicate invoice number, or overdue escalation triggers [done]
17. Wire the full multi-agent flow behind FastAPI endpoints [done]

### Phase 5: Evaluation, UI, And Submission Polish

18. Build a small evaluation dataset and a script for structured-output validity, grounding quality, and latency [done]
19. Build a minimal UI for upload, retrieved evidence, and final decision display [done]
20. Update the README with architecture, workflow, evaluation, known limitations, and demo instructions [done]
21. Record a 60-90 second demo and prepare resume/project bullets [done]

### Phase 6: Stretch Goals

22. Add TTS-safe follow-up text formatting for dates, amounts, and identifiers [done]
23. Add prompt version comparison or A/B evaluation
24. Add an audit trail showing retrieved chunks, prompt version, latency, and final recommendation

## Step Order

```text
Phase 1
  Step 1  Repo skeleton, env file, baseline README
  Step 2  Lock the two workflows: AP approval + AR follow-up
  Step 3  Define Pydantic schemas for extraction and decisions
  Step 4  Write synthetic finance KB docs
  Step 5  Create sample invoices, emails, and expected outputs

Phase 2
  Step 6  Build PDF text extraction [done]
  Step 7  Add OCR fallback for scanned invoices [done]
  Step 8  Build extractor agent with strict JSON output [done]
  Step 9  Add schema validation and retry behavior [done]

Phase 3
  Step 10 Chunk and index the finance KB [done]
  Step 11 Build retrieval with citations [done]
  Step 12 Route cases into AP or AR flows [done]
  Step 13 Assemble grounded policy context for downstream decisions [done]

Phase 4
  Step 14 Build AP recommendation flow [done]
  Step 15 Build AR follow-up drafting flow [done]
  Step 16 Add anomaly flags and escalation triggers [done]
  Step 17 Expose the full flow through FastAPI endpoints [done]

Phase 5
  Step 18 Build eval dataset and eval runner [done]
  Step 19 Build minimal upload/results UI [done]
  Step 20 Finish README with architecture, eval, and limitations [done]
  Step 21 Record demo and prep resume/project bullets [done]

Phase 6
  Step 22 Add TTS-safe follow-up formatting [done]
  Step 23 Add prompt A/B evaluation
  Step 24 Add audit trail for evidence, prompt version, and latency
```

## Files To Create

```text
peakflo-finance-agent-demo/
|- README.md
|- .env.example
|- requirements.txt
|- api/
|  `- main.py
|- app/
|  |- schemas/
|  |  |- invoice.py
|  |  `- decision.py
|  |- ingest/
|  |  |- pdf_reader.py
|  |  |- ocr.py
|  |  `- email_parser.py
|  |- rag/
|  |  |- chunker.py
|  |  |- embed.py
|  |  `- retrieve.py
|  |- agents/
|  |  |- extractor.py
|  |  |- research.py
|  |  |- policy.py
|  |  |- decision.py
|  |  `- editor.py
|  |- orchestrator/
|  |  `- router.py
|  |- prompts/
|  |  |- extractor_v1.md
|  |  |- decision_v1.md
|  |  `- followup_v1.md
|  `- eval/
|     |- dataset.json
|     `- run_eval.py
|- kb/
|  |- approval_matrix.md
|  |- invoice_policy.md
|  |- reminder_templates.md
|  `- vendor_terms.md
|- samples/
|  |- invoices/
|  |- emails/
|  `- expected_outputs/
`- web/
```

## Important Build Rules

- Keep the knowledge base small and synthetic
- Prefer deterministic structure over fancy model behavior
- Validate every major output with a schema
- Show evidence for final decisions
- Keep frontend minimal

## Edge Cases

- Text PDF vs scanned invoice: use OCR fallback only when direct extraction is weak or empty
- Missing or ambiguous fields: return explicit missing-info flags rather than guessing silently
- Retrieval drift: require cited evidence in the final response and keep the KB small and domain-limited
- Invalid model JSON: validate through Pydantic and retry with stricter formatting prompts
- AP vs AR confusion: add a deterministic routing layer before agent reasoning
- Duplicate invoice numbers: include a simple sample rule and anomaly flag even if there is no real database

## Risks

- Scope expands into a full finance product
  - Mitigation: stick to AP approval recommendation and AR follow-up drafting only
- OCR quality becomes a time sink
  - Mitigation: use mostly text-based synthetic invoices first and keep OCR as a fallback
- Project feels like a chatbot
  - Mitigation: force structured outputs, cited evidence, and explicit business actions
- Evaluation gets skipped
  - Mitigation: treat `app/eval/run_eval.py` as required, not optional
- Frontend polish steals time from backend quality
  - Mitigation: keep the UI minimal and leave visual polish for the end

## What Makes This A Strong Peakflo Project

This project should prove:
- you can build Python backend systems
- you understand structured outputs and validation
- you can connect retrieval to business decisions
- you think in workflows, not chatbot demos
- you care about reliability and grounded outputs

## Resume Positioning After Completion

This project should become the first project on the Peakflo resume.

Good bullet themes:
- workflow automation
- structured extraction
- retrieval grounding
- validation
- business-action outputs

Avoid framing it as:
- generic chatbot
- broad AI assistant
- unexplained model demo

## Demo Flow

Best 90-second walkthrough:
1. Upload invoice
2. Show extracted JSON
3. Show retrieved policy evidence
4. Show AP recommendation
5. Switch to overdue AR case
6. Show follow-up draft
7. Show eval summary

## Done When

- A user can upload an invoice or finance email and receive structured JSON plus a grounded action recommendation
- The system can show retrieved policy evidence and explain why the recommendation was made
- The repo includes a minimal eval script, sample cases, and a clear README
- The project can be demoed in under 90 seconds
- The final repo reads like a role-shaped AI workflow system, not a generic model demo
