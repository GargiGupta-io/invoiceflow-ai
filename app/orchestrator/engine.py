"""Run the full finance workflow end-to-end."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from ..agents import (
    ExtractorAgent,
    APWorkflowAssessment,
    ARWorkflowAssessment,
    assemble_grounded_policy_context,
    assess_accounts_payable,
    assess_accounts_receivable,
    decide_accounts_payable,
    draft_accounts_receivable,
)
from ..ingest import read_document_text
from ..rag import build_knowledge_index, load_knowledge_index, save_knowledge_index
from ..schemas.decision import WorkflowResult, WorkflowType
from .router import route_workflow

PROJECT_ROOT = Path(__file__).resolve().parents[2]
KB_DIR = PROJECT_ROOT / "kb"
KB_INDEX_PATH = KB_DIR / "index.json"
SAMPLES_DIR = PROJECT_ROOT / "samples"


def list_sample_documents() -> list[dict[str, str]]:
    """Return the available sample documents exposed by the backend."""

    sample_paths = sorted(
        list((SAMPLES_DIR / "invoices").glob("*.txt"))
        + list((SAMPLES_DIR / "emails").glob("*.txt"))
    )
    return [
        {
            "sample_id": path.stem,
            "path": str(path),
            "category": path.parent.name,
        }
        for path in sample_paths
    ]


def resolve_sample_path(sample_id: str) -> Path:
    """Resolve one sample identifier to its source text file."""

    candidate_paths = [
        SAMPLES_DIR / "invoices" / f"{sample_id}.txt",
        SAMPLES_DIR / "emails" / f"{sample_id}.txt",
    ]
    for path in candidate_paths:
        if path.exists():
            return path
    raise FileNotFoundError(f"Unknown sample id: {sample_id}")


def run_workflow_from_sample(sample_id: str, *, extractor_mode: str = "heuristic") -> dict[str, Any]:
    """Run the full workflow using one of the built-in sample cases."""

    sample_path = resolve_sample_path(sample_id)
    return run_workflow_from_path(sample_path, extractor_mode=extractor_mode, source_kind="sample")


def run_workflow_from_upload(
    filename: str,
    content: bytes,
    *,
    extractor_mode: str = "auto",
) -> dict[str, Any]:
    """Run the workflow for an uploaded file via a temporary staged path."""

    suffix = Path(filename or "upload.txt").suffix or ".txt"
    with NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(content)
        temp_path = Path(temp_file.name)

    try:
        return run_workflow_from_path(
            temp_path,
            extractor_mode=extractor_mode,
            source_kind="upload",
            original_filename=filename,
        )
    finally:
        temp_path.unlink(missing_ok=True)


def run_workflow_from_path(
    path: str | Path,
    *,
    extractor_mode: str = "auto",
    source_kind: str = "file",
    original_filename: str | None = None,
) -> dict[str, Any]:
    """Run ingestion, extraction, routing, retrieval, and final decision flow."""

    source_path = Path(path).expanduser().resolve()
    index = _load_or_build_knowledge_index()
    extractor = ExtractorAgent(mode=extractor_mode)

    document = read_document_text(source_path)
    extraction = extractor.extract(document)
    route = route_workflow(extraction)
    context = assemble_grounded_policy_context(extraction, route, index)

    assessment_payload: dict[str, Any]
    workflow_result: WorkflowResult

    if route.workflow_type == WorkflowType.AP:
        assessment = assess_accounts_payable(extraction, context)
        decision = decide_accounts_payable(extraction, context)
        workflow_result = WorkflowResult(
            workflow_type=route.workflow_type,
            extraction=extraction,
            ap_decision=decision,
        )
        assessment_payload = _serialize_ap_assessment(assessment)
    else:
        assessment = assess_accounts_receivable(extraction, context)
        decision = draft_accounts_receivable(extraction, context)
        workflow_result = WorkflowResult(
            workflow_type=route.workflow_type,
            extraction=extraction,
            ar_decision=decision,
        )
        assessment_payload = _serialize_ar_assessment(assessment)

    return {
        "source": {
            "kind": source_kind,
            "path": str(source_path),
            "filename": original_filename or source_path.name,
        },
        "route": route.to_dict(),
        "grounded_context": context.to_dict(),
        "policy_assessment": assessment_payload,
        "workflow_result": workflow_result.model_dump(mode="json"),
    }


def _load_or_build_knowledge_index():
    if KB_INDEX_PATH.exists():
        return load_knowledge_index(KB_INDEX_PATH)
    index = build_knowledge_index(KB_DIR)
    save_knowledge_index(index, KB_INDEX_PATH)
    return index


def _serialize_ap_assessment(assessment: APWorkflowAssessment) -> dict[str, Any]:
    return {
        "kind": "accounts_payable",
        "vendor_policy": asdict(assessment.vendor_policy),
        "reason_codes": list(assessment.reason_codes),
        "anomalies": [anomaly.model_dump(mode="json") for anomaly in assessment.anomalies],
    }


def _serialize_ar_assessment(assessment: ARWorkflowAssessment) -> dict[str, Any]:
    return {
        "kind": "accounts_receivable",
        "customer_policy": asdict(assessment.customer_policy),
        "escalation_level": assessment.escalation_level.value,
        "payment_claim": assessment.payment_claim,
        "overdue_days": assessment.overdue_days,
        "prior_reminders": assessment.prior_reminders,
        "trigger_codes": list(assessment.trigger_codes),
    }
