"""Build dashboard payloads from the saved eval report."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .run_eval import run_evaluation

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVAL_RESULTS_PATH = PROJECT_ROOT / "eval-results.json"


def build_eval_dashboard(*, refresh: bool = False) -> dict[str, Any]:
    report = _load_eval_report(refresh=refresh)
    summary = report.get("summary", {})
    cases = report.get("cases", [])
    failing_cases = [_build_failing_case(case) for case in cases if not case.get("passed")]
    generated_at_utc = report.get("generated_at_utc") or _file_mtime_utc(EVAL_RESULTS_PATH)

    return {
        "dataset_name": report.get("dataset_name", "invoiceflow-ai-v1"),
        "extractor_mode": report.get("extractor_mode", "heuristic"),
        "generated_at_utc": generated_at_utc,
        "results_url": "/eval-results.json",
        "download_url": "/eval-results.json",
        "refresh_url": "/eval/summary?refresh=1",
        "summary": summary,
        "failing_case_count": len(failing_cases),
        "failing_cases": failing_cases,
    }


def _load_eval_report(*, refresh: bool) -> dict[str, Any]:
    if refresh or not EVAL_RESULTS_PATH.exists():
        report = _generate_eval_report()
        EVAL_RESULTS_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report

    return json.loads(EVAL_RESULTS_PATH.read_text(encoding="utf-8"))


def _generate_eval_report() -> dict[str, Any]:
    return {
        "generated_at_utc": _utc_now(),
        **run_evaluation(),
    }


def _build_failing_case(case: dict[str, Any]) -> dict[str, Any]:
    extraction_checks = case.get("extraction_checks", {})
    decision_checks = case.get("decision_checks", {})
    failed_checks = []

    if not extraction_checks.get("passed", False):
        failed_checks.append("extraction")

    for check in decision_checks.get("checks", []):
        if not check.get("passed", False):
            failed_checks.append(check.get("name") or "decision")

    return {
        "sample_id": case.get("sample_id"),
        "workflow_type": case.get("workflow_type"),
        "latency_ms": case.get("latency_ms"),
        "failed_checks": failed_checks,
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _file_mtime_utc(path: Path) -> str | None:
    if not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
