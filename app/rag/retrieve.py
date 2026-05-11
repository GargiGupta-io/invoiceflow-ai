"""Retrieve citeable finance policy chunks from the knowledge index."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from .embed import KnowledgeIndex

TOKEN_RE = re.compile(r"[a-z0-9]+")
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "if",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}


@dataclass(slots=True)
class RetrievalHit:
    """One ranked, citeable knowledge-base match."""

    chunk_id: str
    source_id: str
    source_file: str
    source_title: str
    section_title: str
    excerpt: str
    score: float
    matched_tokens: list[str]
    relevance_reason: str

    def to_dict(self) -> dict:
        return asdict(self)


def query_knowledge_index(
    index: KnowledgeIndex,
    query_text: str,
    *,
    top_k: int = 5,
    workflow_hint: str | None = None,
) -> list[RetrievalHit]:
    """Rank KB chunks for a workflow query and return citeable matches."""

    query_tokens = _tokenize_query(query_text)
    if not query_tokens:
        return []

    candidate_ids = _collect_candidate_ids(index, query_tokens)
    if not candidate_ids:
        candidate_ids = set(index.chunk_lookup.keys())

    scored_hits: list[RetrievalHit] = []
    for chunk_id in candidate_ids:
        chunk = index.chunk_lookup[chunk_id]
        overlap = [token for token in query_tokens if token in chunk.tokens]
        if not overlap:
            continue

        score = _score_chunk(
            overlap_count=len(overlap),
            query_token_count=len(query_tokens),
            workflow_hint=workflow_hint,
            section_code=chunk.section_code,
            source_file=chunk.source_file,
        )
        scored_hits.append(
            RetrievalHit(
                chunk_id=chunk.chunk_id,
                source_id=chunk.section_code,
                source_file=chunk.source_file,
                source_title=chunk.source_title,
                section_title=chunk.section_title,
                excerpt=chunk.text,
                score=round(score, 4),
                matched_tokens=overlap,
                relevance_reason=_build_relevance_reason(overlap, chunk.section_code),
            )
        )

    ranked_hits = sorted(
        scored_hits,
        key=lambda item: (-item.score, item.source_id, item.section_title),
    )
    return ranked_hits[:top_k]


def hits_to_evidence_payloads(hits: list[RetrievalHit]) -> list[dict[str, str]]:
    """Convert retrieval hits into later decision-friendly evidence payloads."""

    return [
        {
            "source_id": hit.source_id,
            "source_title": f"{hit.source_title} - {hit.section_title}",
            "excerpt": hit.excerpt,
            "relevance_reason": hit.relevance_reason,
        }
        for hit in hits
    ]


def _collect_candidate_ids(index: KnowledgeIndex, query_tokens: list[str]) -> set[str]:
    candidate_ids: set[str] = set()
    for token in query_tokens:
        candidate_ids.update(index.token_to_chunk_ids.get(token, []))
    return candidate_ids


def _tokenize_query(query_text: str) -> list[str]:
    tokens = TOKEN_RE.findall(query_text.lower())
    ordered: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        if len(token) <= 1 or token in STOPWORDS or token in seen:
            continue
        ordered.append(token)
        seen.add(token)
    return ordered


def _score_chunk(
    *,
    overlap_count: int,
    query_token_count: int,
    workflow_hint: str | None,
    section_code: str,
    source_file: str,
) -> float:
    base_score = overlap_count / max(query_token_count, 1)
    workflow_bonus = 0.0

    normalized_hint = (workflow_hint or "").strip().lower()
    if normalized_hint == "ap" and section_code.startswith("AP-"):
        workflow_bonus = 0.35
    elif normalized_hint == "ar" and section_code.startswith("AR-"):
        workflow_bonus = 0.35
    elif normalized_hint == "ap" and source_file == "vendor_terms.md" and section_code.startswith("VENDOR-"):
        workflow_bonus = 0.2
    elif normalized_hint == "ar" and source_file == "vendor_terms.md" and section_code.startswith("CUSTOMER-"):
        workflow_bonus = 0.2

    density_bonus = min(overlap_count * 0.05, 0.2)
    return base_score + workflow_bonus + density_bonus


def _build_relevance_reason(matched_tokens: list[str], section_code: str) -> str:
    token_preview = ", ".join(matched_tokens[:4])
    if token_preview:
        return f"Matches query terms ({token_preview}) and cites {section_code}."
    return f"Cites {section_code} for the current workflow query."
