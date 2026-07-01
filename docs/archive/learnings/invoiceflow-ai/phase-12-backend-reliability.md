# Phase 12: Backend Reliability

> This phase made the InvoiceFlow backend safer around bad inputs by adding structured API errors, upload validation, and focused reliability tests.

---

## In Plain English

InvoiceFlow should not only work when a perfect sample case is selected. A real finance workflow tool also needs to behave well when the user uploads the wrong file, sends an empty document, picks an invalid extractor mode, or asks for a sample that does not exist.

Before this phase, some backend errors returned raw exception messages. That is risky because raw errors can expose implementation details and feel unprofessional to users. This phase changed the API so bad inputs return clear error codes and practical messages.

The result is a backend that feels more production-aware. It tells the frontend what happened, gives the user a next step, and keeps unexpected internal details out of the response.

## What Is Backend Reliability?

Backend reliability means the server behaves predictably under both normal and bad conditions. It is not just about the happy path. It is about what happens when the user sends something unexpected.

For InvoiceFlow, backend reliability includes:

- health endpoint stays available
- sample workflow handles unknown sample IDs
- extractor mode is validated
- empty uploads are rejected
- unsupported file types are rejected
- upload size is limited
- OCR limitations are explained
- internal workflow failures return safe generic errors
- tests cover expected failure paths

This matters because finance workflows involve documents, money, policy, and human review. Users need clear errors, not confusing stack traces.

## The Problem It Solves

Before this phase, the API had useful endpoints but thin boundary checks.

Examples:

```text
POST /workflow/sample
  invalid extractor mode -> raw internal error

POST /workflow/upload
  unsupported file type -> could reach lower ingestion code

POST /workflow/upload
  empty file -> simple string error
```

These responses worked for development, but they were not polished enough for a paid-ready product demo.

The fix was to make the API boundary stricter:

```text
Request enters API
  -> validate extractor mode
  -> validate upload size
  -> validate upload extension
  -> return structured error if invalid
  -> only then run workflow
```

## What We Built

### Structured Error Helper

Plain English: Every expected API error now has a code and message.

File changed:

```text
api/main.py
```

The helper creates responses like:

```json
{
  "code": "unsupported_file_type",
  "message": "Unsupported file type. Upload a text-based PDF, .txt, or .md file.",
  "allowed_extensions": [".md", ".pdf", ".txt"],
  "ocr_note": "OCR is not configured in this environment. Text-based PDFs and pasted text still work."
}
```

This is better than a raw exception string because the frontend can react to `code`, while humans can read `message`.

### Extractor Mode Validation

Plain English: The backend now rejects extractor modes it does not understand before the workflow starts.

Allowed modes:

```text
auto
heuristic
llm
```

If the user sends:

```text
unsafe
```

The API returns:

```text
invalid_extractor_mode
```

This prevents invalid configuration from reaching the extractor layer.

### Upload File Validation

Plain English: The upload endpoint now checks whether the file is empty, too large, or unsupported.

Rules added:

```text
empty file -> 400 empty_upload
file over 5 MB -> 413 upload_too_large
unsupported extension -> 400 unsupported_file_type
```

Supported extensions come from the ingestion layer:

```text
.pdf
.txt
.md
```

This avoids duplicating file-type knowledge across the app. The API asks the ingestion module what it supports.

### OCR/Text Fallback Message

Plain English: If the user uploads the wrong kind of file, the backend explains what still works.

The API now includes:

```text
OCR is not configured in this environment.
Text-based PDFs and pasted text still work.
```

That matters because scanned PDFs are a common source of confusion. The user should know that the app is not silently broken; it just needs extractable text or a text fallback.

### Safer Generic Workflow Errors

Plain English: Unexpected internal failures now return a safe message instead of raw internals.

For sample workflows:

```text
workflow_failed: The sample workflow could not be completed.
```

For uploaded documents:

```text
workflow_failed: The uploaded document workflow could not be completed.
```

This keeps implementation details out of user-facing responses.

### API Reliability Tests

Plain English: The backend now has tests for common bad inputs and one happy-path upload.

File created:

```text
tests/test_api_reliability.py
```

Tests added:

```text
health endpoint reports ok
missing sample returns sample_not_found
invalid extractor mode returns invalid_extractor_mode
empty upload returns empty_upload
unsupported upload type returns unsupported_file_type
text upload still runs workflow
```

These tests prove the backend does not only work for curated demo buttons.

## How It Works

### Request Boundary

Plain English: The API now acts like a front desk that checks whether the request is allowed before sending it deeper into the system.

```text
User request
  |
  v
FastAPI endpoint
  |
  v
validate extractor mode
  |
  v
validate upload file
  |
  v
run workflow
  |
  v
return decision or structured error
```

This is better than letting every bad request reach the deepest workflow logic.

### Error Codes

Plain English: Error codes give the frontend a stable way to understand failures.

Examples:

```text
empty_upload
unsupported_file_type
invalid_extractor_mode
sample_not_found
ingestion_failed
workflow_failed
```

The frontend can eventually map these codes to specific UI states, such as:

```text
show file type hint
show OCR fallback hint
show sample unavailable message
show try again message
```

### Reusing Ingestion Support

Plain English: The API does not guess which file types are supported. It asks the ingestion layer.

The ingestion layer owns:

```text
supported_extensions()
```

That means if support for `.csv` or `.eml` is added later, the API can follow the same source of truth.

## Testing Notes

The files compile with:

```text
python3 -m py_compile api/main.py tests/test_api_reliability.py
```

The local `.venv-local` uses Python 3.9, while the project code uses `dataclass(slots=True)`, which is Python 3.10+ behavior. The existing local preview works around that with a compatibility shim. The reliability tests were run with the same shim and passed:

```text
Ran 6 tests
OK
```

This is important to remember because a clean long-term fix is to run the project under Python 3.10+ or document that requirement clearly.

## Why This Improves InvoiceFlow

This phase improves InvoiceFlow in practical ways.

First, bad inputs are less likely to crash or leak internals.

Second, frontend error states can become more specific because the API now returns stable error codes.

Third, upload behavior is clearer. Users know which files are accepted and what to do when OCR is unavailable.

Fourth, tests prove that failure paths are intentional, not accidental.

## Edge Cases And Gotchas

### Running Server May Need Restart

In plain English: If the preview server was started without reload, it will keep serving old backend code.

Technical cause: The local server on port `8000` was started as a long-running process without auto-reload.

How to avoid: Restart the preview server after backend changes.

### Python Version Mismatch

In plain English: The repo code expects newer Python behavior than the default local `python3`.

Technical cause: `dataclass(slots=True)` requires Python 3.10+, but the local `.venv-local` points to Python 3.9.

How to avoid: Use Python 3.10+ for normal development, or keep the compatibility shim only for local smoke runs.

### Structured Errors Need Frontend Mapping

In plain English: The backend now sends better errors, but the frontend can still be improved to display each error code differently.

Technical cause: The frontend currently formats failures mostly through a generic friendly error function.

How to avoid: In a later phase, map `detail.code` to specific UI copy.

### File Size Limit Is Demo-Oriented

In plain English: Five megabytes is enough for demo files but may be small for real invoice PDFs.

Technical cause: This is a portfolio demo endpoint, not a production document pipeline.

How to avoid: Make the upload limit configurable before real deployment.

## How It Connects To Other Concepts

- **Upload UX**: Backend error codes support better frontend upload messages.
- **Human review**: Bad or weak inputs should route safely instead of producing confident output.
- **Guardrail transparency**: Reliability errors are part of the same trust story as prompt/schema metadata.
- **Evaluation**: Reliability tests complement eval tests by checking API behavior, not just workflow quality.
- **Deployment readiness**: A shareable demo needs stable bad-input behavior.

## Quick Reference

### Files Changed

```text
api/main.py
tests/test_api_reliability.py
steps.md
```

### New Constants

```text
ALLOWED_EXTRACTOR_MODES = {"auto", "heuristic", "llm"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
```

### New API Error Codes

```text
invalid_extractor_mode
empty_upload
upload_too_large
unsupported_file_type
sample_not_found
ingestion_failed
workflow_failed
```

### Tests Added

```text
test_health_endpoint_reports_ok
test_missing_sample_returns_structured_error
test_invalid_extractor_mode_returns_structured_error
test_empty_upload_returns_structured_error
test_unsupported_upload_type_returns_fallback_hint
test_text_upload_still_runs_workflow
```

## Quiz Questions

1. Why are structured error codes better than raw exception strings?
2. Why should upload validation happen at the API boundary?
3. What is the difference between `unsupported_file_type` and `ingestion_failed`?
4. Why does OCR fallback messaging matter for scanned PDFs?
5. Why should backend reliability tests include bad inputs, not only happy paths?

---

*Generated: 2026-06-30 | Project: invoiceflow-ai | Files: api/main.py, tests/test_api_reliability.py, steps.md*
