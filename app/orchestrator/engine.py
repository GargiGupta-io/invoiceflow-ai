"""Run the full finance workflow end-to-end."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from time import perf_counter
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
from .agent_trace import build_agent_tool_trace, build_human_review_gate
from .audit import build_workflow_audit_trail
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


def build_review_queue(*, extractor_mode: str = "heuristic") -> dict[str, Any]:
    """Build a demo review queue from the bundled sample cases."""

    items: list[dict[str, Any]] = []
    for sample in list_sample_documents():
        workflow_payload = run_workflow_from_sample(
            sample["sample_id"],
            extractor_mode=extractor_mode,
        )
        items.append(_review_queue_item(sample["sample_id"], workflow_payload))

    items.sort(key=lambda item: item["timestamp_utc"], reverse=True)
    return {
        "generated_at_utc": _utc_now(),
        "extractor_mode": extractor_mode,
        "item_count": len(items),
        "items": items,
    }


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


def run_workflow_from_sample(
    sample_id: str,
    *,
    extractor_mode: str = "heuristic",
    prompt_path: str | Path | None = None,
) -> dict[str, Any]:
    """Run the full workflow using one of the built-in sample cases."""

    sample_path = resolve_sample_path(sample_id)
    return run_workflow_from_path(
        sample_path,
        extractor_mode=extractor_mode,
        prompt_path=prompt_path,
        source_kind="sample",
    )


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
    prompt_path: str | Path | None = None,
    source_kind: str = "file",
    original_filename: str | None = None,
) -> dict[str, Any]:
    """Run ingestion, extraction, routing, retrieval, and final decision flow."""

    workflow_started = perf_counter()
    stage_latencies_ms: dict[str, float] = {}
    source_path = Path(path).expanduser().resolve()
    stage_started = perf_counter()
    index = _load_or_build_knowledge_index()
    stage_latencies_ms["knowledge_index"] = _elapsed_ms(stage_started)
    extractor_kwargs: dict[str, Any] = {"mode": extractor_mode}
    if prompt_path is not None:
        extractor_kwargs["prompt_path"] = Path(prompt_path).expanduser().resolve()
    extractor = ExtractorAgent(**extractor_kwargs)

    stage_started = perf_counter()
    document = read_document_text(source_path)
    stage_latencies_ms["ingestion"] = _elapsed_ms(stage_started)

    stage_started = perf_counter()
    extraction = extractor.extract(document)
    stage_latencies_ms["extraction"] = _elapsed_ms(stage_started)

    stage_started = perf_counter()
    route = route_workflow(extraction)
    stage_latencies_ms["routing"] = _elapsed_ms(stage_started)

    stage_started = perf_counter()
    context = assemble_grounded_policy_context(extraction, route, index)
    stage_latencies_ms["grounding"] = _elapsed_ms(stage_started)

    assessment_payload: dict[str, Any]
    workflow_result: WorkflowResult
    decision: Any

    stage_started = perf_counter()
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
    stage_latencies_ms["decision"] = _elapsed_ms(stage_started)

    total_latency_ms = _elapsed_ms(workflow_started)
    agent_tool_trace = build_agent_tool_trace(
        extraction=extraction,
        route=route,
        context=context,
        assessment_payload=assessment_payload,
        decision=decision,
    )
    human_review_gate = build_human_review_gate(
        extraction=extraction,
        route=route,
        context=context,
        assessment_payload=assessment_payload,
        decision=decision,
    )
    audit_trail = build_workflow_audit_trail(
        requested_extractor_mode=extractor.mode,
        effective_extractor_mode=extractor.last_mode_used or extractor.mode.lower().strip(),
        prompt_path=extractor.prompt_path,
        repair_prompt_path=extractor.repair_prompt_path,
        route=route,
        context=context,
        decision=decision,
        human_review_gate=human_review_gate,
        agent_tool_trace=agent_tool_trace,
        llm_gateway_metadata=extractor.llm_gateway_metadata,
        stage_latencies_ms=stage_latencies_ms,
        total_latency_ms=total_latency_ms,
    )

    return {
        "source": {
            "kind": source_kind,
            "path": str(source_path),
            "filename": original_filename or source_path.name,
        },
        "audit_trail": audit_trail.to_dict(),
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


def _review_queue_item(sample_id: str, workflow_payload: dict[str, Any]) -> dict[str, Any]:
    audit = workflow_payload.get("audit_trail", {})
    workflow_result = workflow_payload.get("workflow_result", {})
    workflow_type = workflow_result.get("workflow_type", "")
    decision = workflow_result.get("ap_decision") or workflow_result.get("ar_decision") or {}
    human_review = audit.get("human_review", {})
    status = _review_queue_status(workflow_type, decision, human_review)
    risk_level = _review_queue_risk_level(human_review)
    return {
        "case_id": sample_id,
        "workflow_type": workflow_type,
        "recommendation": decision.get("recommendation") or decision.get("escalation_level") or "complete",
        "risk_level": risk_level,
        "reason_for_review": _review_queue_reason(human_review, decision, workflow_type),
        "timestamp_utc": audit.get("generated_at_utc") or _utc_now(),
        "status": status,
    }


def _review_queue_status(
    workflow_type: str,
    decision: dict[str, Any],
    human_review: dict[str, Any],
) -> str:
    if not human_review.get("required"):
        return "Approved"

    if workflow_type == WorkflowType.AP.value:
        recommendation = str(decision.get("recommendation") or "")
        if recommendation == "missing_info":
            return "Returned for Info"
        if recommendation == "reject":
            return "Rejected"
        return "Needs Review"

    escalation_level = str(decision.get("escalation_level") or "")
    if escalation_level == "high":
        return "Escalated"
    if escalation_level in {"low", "medium"}:
        return "Needs Review"
    return "Needs Review"


def _review_queue_risk_level(human_review: dict[str, Any]) -> str:
    if human_review.get("blocking"):
        return "High risk"
    if human_review.get("required"):
        return "Medium risk"
    return "Low risk"


def _review_queue_reason(
    human_review: dict[str, Any],
    decision: dict[str, Any],
    workflow_type: str,
) -> str:
    reason_codes = human_review.get("reason_codes") or []
    if reason_codes:
        return ", ".join(reason_codes)

    if workflow_type == WorkflowType.AP.value:
        recommendation = str(decision.get("recommendation") or "")
        if recommendation == "missing_info":
            return "Missing AP information"
        if recommendation == "reject":
            return "AP rejection"
        return "Manual AP review"

    escalation_level = str(decision.get("escalation_level") or "")
    if escalation_level:
        return f"AR escalation {escalation_level}"
    return "Manual AR review"


def _utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _elapsed_ms(started_at: float) -> float:
    return round((perf_counter() - started_at) * 1000, 2)
