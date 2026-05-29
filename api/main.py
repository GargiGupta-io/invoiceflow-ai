"""FastAPI entrypoint for InvoiceFlow AI."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.eval.dashboard import EVAL_RESULTS_PATH, build_eval_dashboard
from app.orchestrator import list_sample_documents, run_workflow_from_sample, run_workflow_from_upload
from app.orchestrator import build_review_queue

WEB_DIR = Path(__file__).resolve().parents[1] / "web"

app = FastAPI(
    title="InvoiceFlow AI",
    version="0.1.0",
    description=(
        "A finance workflow agent that ingests documents, extracts structured fields, "
        "retrieves grounded policy evidence, routes AP/AR cases, and returns a final decision."
    ),
)

app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


class SampleWorkflowRequest(BaseModel):
    sample_id: str = Field(..., min_length=1, description="Sample identifier from the built-in sample set.")
    extractor_mode: str = Field(
        default="heuristic",
        description="Extractor mode: heuristic, llm, or auto.",
    )


@app.get("/")
def root() -> dict:
    return {
        "name": "InvoiceFlow AI",
        "version": "0.1.0",
        "endpoints": [
            "/ui",
            "/health",
            "/samples",
            "/review-queue",
            "/eval/summary",
            "/eval-results.json",
            "/workflow/sample",
            "/workflow/upload",
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
    try:
        return run_workflow_from_sample(
            request.sample_id,
            extractor_mode=request.extractor_mode,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/workflow/upload")
async def workflow_from_upload(
    file: UploadFile = File(...),
    extractor_mode: str = Form(default="auto"),
    workflow_hint: str = Form(default="ap"),
) -> dict:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        return run_workflow_from_upload(
            filename=file.filename or "upload.txt",
            content=content,
            extractor_mode=extractor_mode,
            workflow_hint=workflow_hint,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
