"""Run the built-in evaluation suite for the finance workflow demo."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from app.orchestrator import run_workflow_from_sample

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET_PATH = Path(__file__).resolve().with_name("dataset.json")


def run_evaluation(
    dataset_path: str | Path = DEFAULT_DATASET_PATH,
    *,
    extractor_mode_override: str | None = None,
    prompt_path_override: str | Path | None = None,
) -> dict[str, Any]:
    """Run the evaluation dataset and return a structured summary."""

    dataset_file = Path(dataset_path).expanduser().resolve()
    dataset = json.loads(dataset_file.read_text(encoding="utf-8"))
    extractor_mode = extractor_mode_override or dataset.get("extractor_mode", "heuristic")

    case_results: list[dict[str, Any]] = []
    for case in dataset.get("cases", []):
        case_results.append(
            _evaluate_case(
                case=case,
                dataset_file=dataset_file,
                extractor_mode=extractor_mode,
                prompt_path=prompt_path_override,
            )
        )

    return {
        "dataset_name": dataset.get("dataset_name", dataset_file.stem),
        "extractor_mode": extractor_mode,
        "prompt_path": str(Path(prompt_path_override).expanduser().resolve()) if prompt_path_override else None,
        "summary": _build_summary(case_results),
        "cases": case_results,
    }


def _evaluate_case(
    *,
    case: dict[str, Any],
    dataset_file: Path,
    extractor_mode: str,
    prompt_path: str | Path | None,
) -> dict[str, Any]:
    sample_id = case["sample_id"]
    expected_output_path = _resolve_expected_output_path(dataset_file, case["expected_output"])
    expected = json.loads(expected_output_path.read_text(encoding="utf-8"))

    started = time.perf_counter()
    actual = run_workflow_from_sample(
        sample_id,
        extractor_mode=extractor_mode,
        prompt_path=prompt_path,
    )
    latency_ms = round((time.perf_counter() - started) * 1000, 2)

    workflow_result = actual["workflow_result"]
    audit_trail = actual.get("audit_trail", {})
    extraction = workflow_result["extraction"]
    decision_payload = workflow_result.get("ap_decision") or workflow_result.get("ar_decision") or {}

    extraction_checks = _evaluate_extraction(
        actual_extraction=extraction,
        expected_extraction=expected.get("expected_extraction", {}),
    )
    decision_checks = _evaluate_decision(
        workflow_type=workflow_result["workflow_type"],
        decision_payload=decision_payload,
        expected_decision=expected.get("expected_decision", {}),
        audit_trail=audit_trail,
    )

    workflow_match = workflow_result["workflow_type"] == expected.get("workflow_type")
    passed = workflow_match and extraction_checks["passed"] and decision_checks["passed"]

    return {
        "sample_id": sample_id,
        "workflow_type": workflow_result["workflow_type"],
        "latency_ms": latency_ms,
        "passed": passed,
        "workflow_match": workflow_match,
        "human_review_required": bool(audit_trail.get("human_review", {}).get("required")),
        "prompt_applied": bool(audit_trail.get("prompt_applied")),
        "rag_repair_attempted": bool(audit_trail.get("retrieval_repair", {}).get("attempted")),
        "rag_repair_success": bool(audit_trail.get("retrieval_repair", {}).get("success")),
        "agent_tool_count": len(audit_trail.get("agent_tool_trace", [])),
        "extraction_checks": extraction_checks,
        "decision_checks": decision_checks,
    }


def _evaluate_extraction(
    *,
    actual_extraction: dict[str, Any],
    expected_extraction: dict[str, Any],
) -> dict[str, Any]:
    field_results: list[dict[str, Any]] = []
    matched = 0

    for field_name, expected_value in expected_extraction.items():
        actual_value = actual_extraction.get(field_name)
        is_match = actual_value == expected_value
        if is_match:
            matched += 1
        field_results.append(
            {
                "field": field_name,
                "expected": expected_value,
                "actual": actual_value,
                "match": is_match,
            }
        )

    total = len(field_results)
    return {
        "passed": matched == total,
        "matched_fields": matched,
        "total_fields": total,
        "field_results": field_results,
    }


def _evaluate_decision(
    *,
    workflow_type: str,
    decision_payload: dict[str, Any],
    expected_decision: dict[str, Any],
    audit_trail: dict[str, Any],
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    if workflow_type == "accounts_payable":
        checks.append(
            _simple_check(
                name="recommendation",
                expected=expected_decision.get("recommendation"),
                actual=decision_payload.get("recommendation"),
            )
        )
    else:
        checks.append(
            _simple_check(
                name="escalation_level",
                expected=expected_decision.get("escalation_level"),
                actual=decision_payload.get("escalation_level"),
            )
        )

    checks.append(
        _citation_check(
            expected_source_ids=expected_decision.get("must_cite", []),
            actual_evidence=decision_payload.get("evidence", []),
        )
    )
    checks.append(
        _grounding_support_check(
            actual_evidence=decision_payload.get("evidence", []),
            retrieved_chunks=audit_trail.get("retrieved_chunks", []),
        )
    )

    if "must_flag_anomalies" in expected_decision:
        checks.append(
            _anomaly_check(
                expected_codes=expected_decision.get("must_flag_anomalies", []),
                actual_anomalies=decision_payload.get("anomalies", []),
            )
        )

    if "followup_subject_contains" in expected_decision:
        checks.append(
            _contains_check(
                name="followup_subject_contains",
                expected_fragments=expected_decision.get("followup_subject_contains", []),
                actual_text=decision_payload.get("followup_subject", ""),
            )
        )

    if "must_mention" in expected_decision:
        checks.append(
            _contains_check(
                name="followup_draft_mentions",
                expected_fragments=expected_decision.get("must_mention", []),
                actual_text=decision_payload.get("followup_draft", ""),
            )
        )

    return {
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
    }


def _simple_check(*, name: str, expected: Any, actual: Any) -> dict[str, Any]:
    return {
        "name": name,
        "expected": expected,
        "actual": actual,
        "passed": expected == actual,
    }


def _citation_check(*, expected_source_ids: list[str], actual_evidence: list[dict[str, Any]]) -> dict[str, Any]:
    actual_ids = [item.get("source_id") for item in actual_evidence]
    missing_ids = [source_id for source_id in expected_source_ids if source_id not in actual_ids]
    return {
        "name": "citation_coverage",
        "expected": expected_source_ids,
        "actual": actual_ids,
        "missing": missing_ids,
        "passed": not missing_ids,
    }


def _grounding_support_check(
    *,
    actual_evidence: list[dict[str, Any]],
    retrieved_chunks: list[dict[str, Any]],
) -> dict[str, Any]:
    retrieved_ids = {item.get("source_id") for item in retrieved_chunks}
    evidence_ids = [item.get("source_id") for item in actual_evidence]
    unsupported_ids = [
        source_id
        for source_id in evidence_ids
        if source_id and source_id != "context-summary" and source_id not in retrieved_ids
    ]
    return {
        "name": "grounding_support",
        "expected": "all cited evidence source IDs are present in retrieved chunks",
        "actual": evidence_ids,
        "unsupported": unsupported_ids,
        "passed": not unsupported_ids,
    }


def _anomaly_check(*, expected_codes: list[str], actual_anomalies: list[dict[str, Any]]) -> dict[str, Any]:
    actual_codes = [item.get("code") for item in actual_anomalies]
    missing_codes = [code for code in expected_codes if code not in actual_codes]
    return {
        "name": "anomaly_coverage",
        "expected": expected_codes,
        "actual": actual_codes,
        "missing": missing_codes,
        "passed": not missing_codes,
    }


def _contains_check(*, name: str, expected_fragments: list[str], actual_text: str) -> dict[str, Any]:
    lowered_text = actual_text.lower()
    missing_fragments = [
        fragment for fragment in expected_fragments if fragment.lower() not in lowered_text
    ]
    return {
        "name": name,
        "expected": expected_fragments,
        "actual": actual_text,
        "missing": missing_fragments,
        "passed": not missing_fragments,
    }


def _build_summary(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    total_cases = len(case_results)
    passed_cases = sum(1 for case in case_results if case["passed"])
    workflow_matches = sum(1 for case in case_results if case["workflow_match"])

    extraction_field_matches = sum(
        case["extraction_checks"]["matched_fields"] for case in case_results
    )
    extraction_field_total = sum(
        case["extraction_checks"]["total_fields"] for case in case_results
    )

    citation_checks = _collect_check_stats(case_results, "citation_coverage")
    grounding_checks = _collect_check_stats(case_results, "grounding_support")
    anomaly_checks = _collect_check_stats(case_results, "anomaly_coverage")
    subject_checks = _collect_check_stats(case_results, "followup_subject_contains")
    mention_checks = _collect_check_stats(case_results, "followup_draft_mentions")
    human_review_cases = sum(1 for case in case_results if case["human_review_required"])
    prompt_applied_cases = sum(1 for case in case_results if case["prompt_applied"])
    rag_repair_attempted_cases = sum(1 for case in case_results if case["rag_repair_attempted"])
    rag_repair_success_cases = sum(1 for case in case_results if case["rag_repair_success"])
    average_agent_tools = round(
        sum(case["agent_tool_count"] for case in case_results) / max(total_cases, 1),
        2,
    )

    average_latency_ms = round(
        sum(case["latency_ms"] for case in case_results) / max(total_cases, 1),
        2,
    )

    return {
        "total_cases": total_cases,
        "passed_cases": passed_cases,
        "pass_rate": round(passed_cases / max(total_cases, 1), 4),
        "workflow_match_rate": round(workflow_matches / max(total_cases, 1), 4),
        "extraction_field_match_rate": round(
            extraction_field_matches / max(extraction_field_total, 1),
            4,
        ),
        "citation_check_pass_rate": _rate(citation_checks["passed"], citation_checks["total"]),
        "grounding_support_pass_rate": _rate(grounding_checks["passed"], grounding_checks["total"]),
        "anomaly_check_pass_rate": _rate(anomaly_checks["passed"], anomaly_checks["total"]),
        "subject_check_pass_rate": _rate(subject_checks["passed"], subject_checks["total"]),
        "mention_check_pass_rate": _rate(mention_checks["passed"], mention_checks["total"]),
        "human_review_rate": round(human_review_cases / max(total_cases, 1), 4),
        "prompt_applied_rate": round(prompt_applied_cases / max(total_cases, 1), 4),
        "rag_repair_attempt_rate": round(rag_repair_attempted_cases / max(total_cases, 1), 4),
        "rag_repair_success_rate": round(rag_repair_success_cases / max(total_cases, 1), 4),
        "average_agent_tool_calls": average_agent_tools,
        "average_latency_ms": average_latency_ms,
    }


def _collect_check_stats(case_results: list[dict[str, Any]], check_name: str) -> dict[str, int]:
    total = 0
    passed = 0
    for case in case_results:
        for check in case["decision_checks"]["checks"]:
            if check["name"] != check_name:
                continue
            total += 1
            if check["passed"]:
                passed += 1
    return {"total": total, "passed": passed}


def _rate(passed: int, total: int) -> float | None:
    if total == 0:
        return None
    return round(passed / total, 4)


def _resolve_expected_output_path(dataset_file: Path, relative_path: str) -> Path:
    return (dataset_file.parents[2] / relative_path).resolve()


def main() -> None:
    result = run_evaluation()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
