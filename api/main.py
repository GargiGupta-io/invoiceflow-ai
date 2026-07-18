"""FastAPI entrypoint for InvoiceFlow AI."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from api.v2 import router as v2_router
from app.auth.dependencies import get_database
from app.config import get_settings
from app.eval.dashboard import EVAL_RESULTS_PATH, build_eval_dashboard
from app.ingest import IngestionError, supported_extensions
from app.orchestrator import list_sample_documents, run_workflow_from_sample, run_workflow_from_upload
from app.orchestrator import build_review_queue
from app.observability import ReadinessChecker
from app.queue import get_processing_queue
from app.storage import get_object_storage

WEB_DIR = Path(__file__).resolve().parents[1] / "web"
ALLOWED_EXTRACTOR_MODES = {"auto", "heuristic", "llm"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024

app = FastAPI(
    title="InvoiceFlow AI",
    version="0.1.0",
    description=(
        "An AI-assisted finance workflow for policy-grounded invoice review, "
        "human review, and deterministic evaluations."
    ),
)

app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
app.include_router(v2_router)


class SampleWorkflowRequest(BaseModel):
    sample_id: str = Field(..., min_length=1, description="Sample identifier from the built-in sample set.")
    extractor_mode: str = Field(
        default="heuristic",
        description="Extractor mode: heuristic, llm, or auto.",
    )


def _error(code: str, message: str, **extra: object) -> dict:
    payload: dict[str, object] = {
        "code": code,
        "message": message,
    }
    payload.update(extra)
    return payload


def _validate_extractor_mode(extractor_mode: str) -> str:
    normalized = extractor_mode.lower().strip()
    if normalized not in ALLOWED_EXTRACTOR_MODES:
        allowed = sorted(ALLOWED_EXTRACTOR_MODES)
        raise HTTPException(
            status_code=400,
            detail=_error(
                "invalid_extractor_mode",
                "Extractor mode must be one of: auto, heuristic, llm.",
                allowed=allowed,
            ),
        )
    return normalized


def _validate_upload_file(filename: str, content: bytes) -> None:
    if not content:
        raise HTTPException(
            status_code=400,
            detail=_error("empty_upload", "Uploaded file is empty."),
        )

    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=_error(
                "upload_too_large",
                "Uploaded file is too large for this demo endpoint.",
                max_bytes=MAX_UPLOAD_BYTES,
            ),
        )

    suffix = Path(filename or "").suffix.lower()
    allowed_extensions = supported_extensions()
    if suffix not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=_error(
                "unsupported_file_type",
                "Unsupported file type. Upload a text-based PDF, .txt, or .md file.",
                allowed_extensions=list(allowed_extensions),
                ocr_note="OCR is not configured in this environment. Text-based PDFs and pasted text still work.",
            ),
        )


@lru_cache
def get_readiness_checker() -> ReadinessChecker:
    settings = get_settings()
    storage_factory = get_object_storage if settings.s3_configured else None
    queue_factory = get_processing_queue if settings.sqs_configured else None
    return ReadinessChecker(
        database=get_database(),
        storage_factory=storage_factory,
        queue_factory=queue_factory,
    )


@app.get("/")
def root() -> dict:
    return {
        "name": "InvoiceFlow AI",
        "version": "0.1.0",
        "endpoints": [
            "/ui",
            "/health",
            "/health/live",
            "/health/ready",
            "/samples",
            "/review-queue",
            "/eval/summary",
            "/eval-results.json",
            "/workflow/sample",
            "/workflow/upload",
            "/v2/me",
            "/v2/documents",
        ],
    }


@app.get("/ui", response_class=FileResponse)
def ui() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "sample_count": len(list_sample_documents()),
    }


@app.get("/health/live")
def health_live() -> dict[str, str]:
    return {"status": "ok", "service": "invoiceflow-api"}


@app.get("/health/ready")
def health_ready(
    checker: ReadinessChecker = Depends(get_readiness_checker),
) -> JSONResponse:
    report = checker.check()
    return JSONResponse(
        status_code=status.HTTP_200_OK if report.ready else status.HTTP_503_SERVICE_UNAVAILABLE,
        content=report.to_dict(),
    )


@app.get("/samples")
def samples() -> dict:
    return {"samples": list_sample_documents()}


@app.get("/review-queue")
def review_queue() -> dict:
    return build_review_queue()


@app.get("/eval/summary")
def eval_summary(refresh: bool = False) -> dict:
    return build_eval_dashboard(refresh=refresh)


@app.get("/eval-results.json", response_class=FileResponse)
def eval_results() -> FileResponse:
    if not EVAL_RESULTS_PATH.exists():
        raise HTTPException(status_code=404, detail="Evaluation results are not available yet.")
    return FileResponse(EVAL_RESULTS_PATH, media_type="application/json", filename="eval-results.json")


@app.post("/workflow/sample")
def workflow_from_sample(request: SampleWorkflowRequest) -> dict:
    extractor_mode = _validate_extractor_mode(request.extractor_mode)
    try:
        return run_workflow_from_sample(
            request.sample_id,
            extractor_mode=extractor_mode,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=_error("sample_not_found", str(exc)),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=_error("workflow_failed", "The sample workflow could not be completed."),
        ) from exc


@app.post("/workflow/upload")
async def workflow_from_upload(
    file: UploadFile = File(...),
    extractor_mode: str = Form(default="auto"),
    workflow_hint: str = Form(default="ap"),
) -> dict:
    extractor_mode = _validate_extractor_mode(extractor_mode)
    content = await file.read()
    filename = file.filename or "upload.txt"
    _validate_upload_file(filename, content)

    try:
        return run_workflow_from_upload(
            filename=filename,
            content=content,
            extractor_mode=extractor_mode,
            workflow_hint=workflow_hint,
        )
    except IngestionError as exc:
        raise HTTPException(
            status_code=400,
            detail=_error(
                "ingestion_failed",
                str(exc),
                fallback="Try a text-based PDF, .txt, .md, or pasted text converted to .txt.",
            ),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=_error("workflow_failed", "The uploaded document workflow could not be completed."),
        ) from exc
