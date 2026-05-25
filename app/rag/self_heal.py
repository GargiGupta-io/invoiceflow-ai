"""Self-healing retrieval helpers for grounded finance policy context."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .embed import KnowledgeIndex
from .retrieve import RetrievalHit, query_knowledge_index


@dataclass(slots=True)
class RetrievalRepairReport:
    """Structured report for one retrieval repair attempt."""

    attempted: bool
    success: bool
    required_source_ids: list[str]
    missing_source_ids_before: list[str]
    missing_source_ids_after: list[str]
    repair_query: str | None
    original_source_ids: list[str]
    final_source_ids: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def repair_retrieval_if_needed(
    *,
    index: KnowledgeIndex,
    query_text: str,
    initial_hits: list[RetrievalHit],
    required_source_ids: list[str],
    workflow_hint: str,
    top_k: int,
) -> tuple[list[RetrievalHit], RetrievalRepairReport]:
    """Retry retrieval with an expanded query when required sources are missing."""

    unique_required = _dedupe(required_source_ids)
    original_source_ids = [hit.source_id for hit in initial_hits]
    missing_before = _missing_source_ids(unique_required, original_source_ids)
    if not missing_before:
        return initial_hits, RetrievalRepairReport(
            attempted=False,
            success=True,
            required_source_ids=unique_required,
            missing_source_ids_before=[],
            missing_source_ids_after=[],
            repair_query=None,
            original_source_ids=original_source_ids,
            final_source_ids=original_source_ids,
        )

    repair_query = build_repair_query(query_text, missing_before)
    repair_hits = query_knowledge_index(
        index,
        repair_query,
        top_k=max(top_k, len(unique_required)),
        workflow_hint=workflow_hint,
    )
    final_hits = _merge_hits(initial_hits, repair_hits, limit=top_k)
    final_source_ids = [hit.source_id for hit in final_hits]
    missing_after = _missing_source_ids(unique_required, final_source_ids)

    return final_hits, RetrievalRepairReport(
        attempted=True,
        success=not missing_after,
        required_source_ids=unique_required,
        missing_source_ids_before=missing_before,
        missing_source_ids_after=missing_after,
        repair_query=repair_query,
        original_source_ids=original_source_ids,
        final_source_ids=final_source_ids,
    )


def build_repair_query(query_text: str, missing_source_ids: list[str]) -> str:
    """Build a second-pass retrieval query that directly names missing policies."""

    missing = " ".join(missing_source_ids)
    source_terms = " ".join(source_id.replace("-", " ") for source_id in missing_source_ids)
    return (
        f"{query_text} | required policy sources {missing} | "
        f"retrieve sections {source_terms}"
    )


def _merge_hits(
    initial_hits: list[RetrievalHit],
    repair_hits: list[RetrievalHit],
    *,
    limit: int,
) -> list[RetrievalHit]:
    merged: list[RetrievalHit] = []
    seen_source_ids: set[str] = set()

    for hit in initial_hits + repair_hits:
        if hit.source_id in seen_source_ids:
            continue
        merged.append(hit)
        seen_source_ids.add(hit.source_id)
        if len(merged) >= limit:
            break

    return merged


def _missing_source_ids(required_source_ids: list[str], actual_source_ids: list[str]) -> list[str]:
    actual = set(actual_source_ids)
    return [source_id for source_id in required_source_ids if source_id not in actual]


def _dedupe(values: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = value.strip()
        if item and item not in seen:
            ordered.append(item)
            seen.add(item)
    return ordered
