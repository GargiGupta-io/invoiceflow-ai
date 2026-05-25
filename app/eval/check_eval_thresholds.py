"""Run evals and fail when quality metrics drop below configured thresholds."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.eval.run_eval import DEFAULT_DATASET_PATH, run_evaluation


DEFAULT_MIN_THRESHOLDS = {
    "pass_rate": 1.0,
    "workflow_match_rate": 1.0,
    "extraction_field_match_rate": 1.0,
    "citation_check_pass_rate": 1.0,
    "grounding_support_pass_rate": 1.0,
    "anomaly_check_pass_rate": 1.0,
    "subject_check_pass_rate": 1.0,
    "mention_check_pass_rate": 1.0,
    "rag_repair_success_rate": 1.0,
}
DEFAULT_MAX_THRESHOLDS = {
    "average_latency_ms": 1000.0,
}


def check_thresholds(
    eval_result: dict[str, Any],
    *,
    min_thresholds: dict[str, float],
    max_thresholds: dict[str, float],
) -> dict[str, Any]:
    """Compare eval summary metrics against CI thresholds."""

    summary = eval_result.get("summary", {})
    checks: list[dict[str, Any]] = []

    for metric_name, threshold in min_thresholds.items():
        actual = summary.get(metric_name)
        passed = actual is not None and float(actual) >= threshold
        checks.append(
            {
                "metric": metric_name,
                "operator": ">=",
                "threshold": threshold,
                "actual": actual,
                "passed": passed,
            }
        )

    for metric_name, threshold in max_thresholds.items():
        actual = summary.get(metric_name)
        passed = actual is not None and float(actual) <= threshold
        checks.append(
            {
                "metric": metric_name,
                "operator": "<=",
                "threshold": threshold,
                "actual": actual,
                "passed": passed,
            }
        )

    failed_checks = [check for check in checks if not check["passed"]]
    return {
        "passed": not failed_checks,
        "checks": checks,
        "failed_checks": failed_checks,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run InvoiceFlow AI evals and enforce CI quality thresholds.",
    )
    parser.add_argument(
        "--dataset",
        default=str(DEFAULT_DATASET_PATH),
        help="Path to the eval dataset JSON.",
    )
    parser.add_argument(
        "--extractor-mode",
        default=None,
        choices=["heuristic", "auto", "llm"],
        help="Optional extractor mode override.",
    )
    parser.add_argument(
        "--prompt-path",
        default=None,
        help="Optional extractor prompt path override.",
    )
    parser.add_argument(
        "--output",
        default="eval-results.json",
        help="Where to write the full eval result and threshold report.",
    )
    parser.add_argument("--min-pass-rate", type=float, default=DEFAULT_MIN_THRESHOLDS["pass_rate"])
    parser.add_argument(
        "--min-workflow-match-rate",
        type=float,
        default=DEFAULT_MIN_THRESHOLDS["workflow_match_rate"],
    )
    parser.add_argument(
        "--min-extraction-field-match-rate",
        type=float,
        default=DEFAULT_MIN_THRESHOLDS["extraction_field_match_rate"],
    )
    parser.add_argument(
        "--min-citation-check-pass-rate",
        type=float,
        default=DEFAULT_MIN_THRESHOLDS["citation_check_pass_rate"],
    )
    parser.add_argument(
        "--min-grounding-support-pass-rate",
        type=float,
        default=DEFAULT_MIN_THRESHOLDS["grounding_support_pass_rate"],
    )
    parser.add_argument(
        "--min-anomaly-check-pass-rate",
        type=float,
        default=DEFAULT_MIN_THRESHOLDS["anomaly_check_pass_rate"],
    )
    parser.add_argument(
        "--min-subject-check-pass-rate",
        type=float,
        default=DEFAULT_MIN_THRESHOLDS["subject_check_pass_rate"],
    )
    parser.add_argument(
        "--min-mention-check-pass-rate",
        type=float,
        default=DEFAULT_MIN_THRESHOLDS["mention_check_pass_rate"],
    )
    parser.add_argument(
        "--min-rag-repair-success-rate",
        type=float,
        default=DEFAULT_MIN_THRESHOLDS["rag_repair_success_rate"],
    )
    parser.add_argument(
        "--max-average-latency-ms",
        type=float,
        default=DEFAULT_MAX_THRESHOLDS["average_latency_ms"],
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    eval_result = run_evaluation(
        dataset_path=args.dataset,
        extractor_mode_override=args.extractor_mode,
        prompt_path_override=args.prompt_path,
    )
    threshold_result = check_thresholds(
        eval_result,
        min_thresholds={
            "pass_rate": args.min_pass_rate,
            "workflow_match_rate": args.min_workflow_match_rate,
            "extraction_field_match_rate": args.min_extraction_field_match_rate,
            "citation_check_pass_rate": args.min_citation_check_pass_rate,
            "grounding_support_pass_rate": args.min_grounding_support_pass_rate,
            "anomaly_check_pass_rate": args.min_anomaly_check_pass_rate,
            "subject_check_pass_rate": args.min_subject_check_pass_rate,
            "mention_check_pass_rate": args.min_mention_check_pass_rate,
            "rag_repair_success_rate": args.min_rag_repair_success_rate,
        },
        max_thresholds={
            "average_latency_ms": args.max_average_latency_ms,
        },
    )

    report = {
        **eval_result,
        "threshold_report": threshold_result,
    }
    output_path = Path(args.output).expanduser().resolve()
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps({"summary": eval_result["summary"], "threshold_report": threshold_result}, indent=2))
    if not threshold_result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
