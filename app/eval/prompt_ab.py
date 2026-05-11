"""Compare extractor prompt variants with structural and optional runtime evaluation."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"
DEFAULT_DATASET_PATH = Path(__file__).resolve().with_name("dataset.json")
PROMPT_VARIANTS = {
    "extractor_v1": PROMPTS_DIR / "extractor_v1.md",
    "extractor_v2": PROMPTS_DIR / "extractor_v2.md",
}

PROMPT_RULES = {
    "json_only": ("return json only", "do not wrap it in markdown"),
    "no_invention": ("do not invent", "grounded"),
    "null_for_unknown": ("use `null`", "unknown"),
    "strict_fields": ("exactly these fields", "do not add extra keys"),
    "source_excerpt_copy": ("source_text_excerpt", "copied from the"),
    "line_items_guard": ("line_items", "present"),
    "ambiguity_warnings": ("ambigu", "warnings"),
    "date_normalization": ("yyyy-mm-dd", "date"),
    "critical_missing_fields": ("missing_fields", "invoice number"),
}


def compare_prompt_variants(
    dataset_path: str | Path = DEFAULT_DATASET_PATH,
    *,
    extractor_mode: str = "llm",
) -> dict[str, Any]:
    """Compare prompt variants structurally and, when possible, at runtime."""

    structural_results = {
        name: _score_prompt_structure(path)
        for name, path in PROMPT_VARIANTS.items()
    }

    runtime_results: dict[str, Any] = {}
    runtime_skipped_reason: str | None = None

    if extractor_mode != "llm":
        runtime_skipped_reason = (
            "Runtime prompt comparison was skipped because prompt variants only affect llm extraction mode."
        )
    elif not os.getenv("OPENAI_API_KEY"):
        runtime_skipped_reason = (
            "Runtime prompt comparison was skipped because OPENAI_API_KEY is not configured."
        )
    else:
        from .run_eval import run_evaluation

        for name, path in PROMPT_VARIANTS.items():
            runtime_results[name] = run_evaluation(
                dataset_path=dataset_path,
                extractor_mode_override="llm",
                prompt_path_override=path,
            )

    winner = _pick_winner(structural_results, runtime_results)

    return {
        "dataset_path": str(Path(dataset_path).expanduser().resolve()),
        "extractor_mode": extractor_mode,
        "variants": {
            name: {
                "prompt_path": str(path),
                "structural_audit": structural_results[name],
                "runtime_eval": runtime_results.get(name),
            }
            for name, path in PROMPT_VARIANTS.items()
        },
        "runtime_skipped_reason": runtime_skipped_reason,
        "winner": winner,
    }


def _score_prompt_structure(prompt_path: Path) -> dict[str, Any]:
    prompt_text = prompt_path.read_text(encoding="utf-8")
    lowered_text = prompt_text.lower()

    checks: list[dict[str, Any]] = []
    passed_count = 0

    for rule_name, fragments in PROMPT_RULES.items():
        passed = all(fragment in lowered_text for fragment in fragments)
        if passed:
            passed_count += 1
        checks.append(
            {
                "name": rule_name,
                "fragments": list(fragments),
                "passed": passed,
            }
        )

    return {
        "passed_checks": passed_count,
        "total_checks": len(PROMPT_RULES),
        "score": round(passed_count / max(len(PROMPT_RULES), 1), 4),
        "checks": checks,
    }


def _pick_winner(
    structural_results: dict[str, dict[str, Any]],
    runtime_results: dict[str, Any],
) -> dict[str, Any]:
    if runtime_results:
        ranked = sorted(
            runtime_results.items(),
            key=lambda item: (
                item[1]["summary"]["pass_rate"],
                item[1]["summary"]["extraction_field_match_rate"],
                item[1]["summary"]["citation_check_pass_rate"] or 0.0,
            ),
            reverse=True,
        )
        best_name, best_result = ranked[0]
        return {
            "variant": best_name,
            "basis": "runtime_eval",
            "summary": best_result["summary"],
        }

    ranked = sorted(
        structural_results.items(),
        key=lambda item: item[1]["score"],
        reverse=True,
    )
    best_name, best_result = ranked[0]
    return {
        "variant": best_name,
        "basis": "structural_audit",
        "summary": {
            "score": best_result["score"],
            "passed_checks": best_result["passed_checks"],
            "total_checks": best_result["total_checks"],
        },
    }


def main() -> None:
    result = compare_prompt_variants()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
