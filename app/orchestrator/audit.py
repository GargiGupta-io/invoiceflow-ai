"""Audit-trail helpers for workflow observability."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from ..schemas.decision import APDecision, ARDecision
from ..schemas.decision import WorkflowType
from ..agents.research import GroundedPolicyContext
from .agent_trace import AgentToolTrace, HumanReviewGate


class WorkflowRouteLike(Protocol):
    workflow_type: Any
    reason: str
    matched_signals: list[str]


@dataclass(slots=True)
class WorkflowAuditTrail:
    generated_at_utc: str
    requested_extractor_mode: str
    effective_extractor_mode: str
    prompt_version: str
    prompt_path: str
    repair_prompt_version: str
    repair_prompt_path: str
    prompt_applied: bool
    llm_gateway: list[dict[str, Any]]
    stage_latencies_ms: dict[str, float]
    total_latency_ms: float
    route_reason: str
    matched_signals: list[str]
    retrieval_query: str
    retrieval_repair: dict[str, Any]
    final_recommendation: dict[str, Any]
    human_review: dict[str, Any]
    agent_tool_trace: list[dict[str, Any]]
    evidence_sources: list[dict[str, Any]]
    retrieved_chunks: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_workflow_audit_trail(
    *,
    requested_extractor_mode: str,
    effective_extractor_mode: str,
    prompt_path: Path,
    repair_prompt_path: Path,
    route: WorkflowRouteLike,
    context: GroundedPolicyContext,
    decision: APDecision | ARDecision,
    human_review_gate: HumanReviewGate,
    agent_tool_trace: list[AgentToolTrace],
    llm_gateway_metadata: list[dict[str, Any]],
    stage_latencies_ms: dict[str, float],
    total_latency_ms: float,
) -> WorkflowAuditTrail:
    """Build one structured observability payload for a workflow run."""

    return WorkflowAuditTrail(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        requested_extractor_mode=requested_extractor_mode,
        effective_extractor_mode=effective_extractor_mode,
        prompt_version=prompt_path.stem,
        prompt_path=str(prompt_path),
        repair_prompt_version=repair_prompt_path.stem,
        repair_prompt_path=str(repair_prompt_path),
        prompt_applied=effective_extractor_mode.startswith("llm"),
        llm_gateway=list(llm_gateway_metadata),
        stage_latencies_ms=dict(stage_latencies_ms),
        total_latency_ms=round(total_latency_ms, 2),
        route_reason=route.reason,
        matched_signals=list(route.matched_signals),
        retrieval_query=context.query_text,
        retrieval_repair=context.retrieval_repair.to_dict(),
        final_recommendation=_build_final_recommendation(route.workflow_type, decision),
        human_review=human_review_gate.to_dict(),
        agent_tool_trace=[trace.to_dict() for trace in agent_tool_trace],
        evidence_sources=_serialize_evidence_sources(decision),
        retrieved_chunks=_serialize_retrieved_chunks(context),
    )


def _build_final_recommendation(
    workflow_type: Any,
    decision: APDecision | ARDecision,
) -> dict[str, Any]:
    normalized_workflow_type = _workflow_type_value(workflow_type)
    if normalized_workflow_type == WorkflowType.AP.value:
        return {
            "workflow_type": normalized_workflow_type,
            "kind": "approval_recommendation",
            "value": _enumish_value(decision.recommendation),
            "summary": decision.reviewer_summary,
            "confidence": decision.confidence,
        }

    return {
        "workflow_type": normalized_workflow_type,
        "kind": "ar_escalation_level",
        "value": _enumish_value(decision.escalation_level),
        "summary": decision.followup_subject,
        "confidence": decision.confidence,
    }


def _serialize_evidence_sources(decision: APDecision | ARDecision) -> list[dict[str, Any]]:
    return [
        {
            "source_id": item.source_id,
            "source_title": item.source_title,
            "relevance_reason": item.relevance_reason,
        }
        for item in decision.evidence
    ]


def _serialize_retrieved_chunks(context: GroundedPolicyContext) -> list[dict[str, Any]]:
    return [
        {
            "chunk_id": hit.chunk_id,
            "source_id": hit.source_id,
            "source_title": hit.source_title,
            "section_title": hit.section_title,
            "score": hit.score,
            "matched_tokens": list(hit.matched_tokens),
        }
        for hit in context.retrieval_hits
    ]


def _workflow_type_value(raw_value: Any) -> str:
    if hasattr(raw_value, "value"):
        return str(raw_value.value)
    return str(raw_value)


def _enumish_value(raw_value: Any) -> str:
    if hasattr(raw_value, "value"):
        return str(raw_value.value)
    return str(raw_value)
