from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Iterable

from sqlalchemy import delete, func, literal_column, or_, select
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentPage
from app.db.repositories.base import TenantRepository
from app.db.repositories.documents import DocumentRepository
from app.db.tenant import TenantContext


@dataclass(frozen=True)
class DocumentPageInput:
    page_number: int
    text: str
    extraction_method: str
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class DocumentSearchHit:
    document_id: uuid.UUID
    page_number: int
    excerpt: str
    extraction_method: str
    score: float


class DocumentPageRepository(TenantRepository):
    def __init__(self, session: Session, tenant: TenantContext) -> None:
        super().__init__(session, tenant)

    def replace_for_document(
        self,
        document_id: uuid.UUID,
        pages: Iterable[DocumentPageInput],
    ) -> list[DocumentPage]:
        DocumentRepository(self.session, self.tenant).require(document_id)
        normalized = self._validate_pages(pages)
        self.purge_for_document(document_id)
        records = [
            DocumentPage(
                organization_id=self.tenant.organization_id,
                document_id=document_id,
                page_number=page.page_number,
                text_content=page.text,
                extraction_method=page.extraction_method,
                warnings=list(page.warnings),
            )
            for page in normalized
        ]
        self.session.add_all(records)
        self.session.flush()
        return records

    def list_for_document(self, document_id: uuid.UUID) -> list[DocumentPage]:
        DocumentRepository(self.session, self.tenant).require(document_id)
        statement = (
            select(DocumentPage)
            .where(
                DocumentPage.organization_id == self.tenant.organization_id,
                DocumentPage.document_id == document_id,
            )
            .order_by(DocumentPage.page_number.asc())
        )
        return list(self.session.scalars(statement))

    def search(self, query: str, *, limit: int = 20) -> list[DocumentSearchHit]:
        search_text = query.strip()
        if not 2 <= len(search_text) <= 200:
            raise ValueError("Search query must contain between 2 and 200 characters.")
        if not 1 <= limit <= 50:
            raise ValueError("Search result limit must be between 1 and 50.")

        if self.session.get_bind().dialect.name == "postgresql":
            rows = self._search_postgresql(search_text, limit=limit)
        else:
            rows = self._search_portable(search_text, limit=limit)
        return [
            DocumentSearchHit(
                document_id=page.document_id,
                page_number=page.page_number,
                excerpt=_build_excerpt(page.text_content, search_text),
                extraction_method=page.extraction_method,
                score=round(float(score), 6),
            )
            for page, score in rows
        ]

    def purge_for_document(self, document_id: uuid.UUID) -> int:
        result = self.session.execute(
            delete(DocumentPage).where(
                DocumentPage.organization_id == self.tenant.organization_id,
                DocumentPage.document_id == document_id,
            )
        )
        self.session.flush()
        return result.rowcount or 0

    def _search_postgresql(
        self,
        query: str,
        *,
        limit: int,
    ) -> list[tuple[DocumentPage, float]]:
        language = literal_column("'english'")
        vector = func.to_tsvector(language, DocumentPage.text_content)
        ts_query = func.websearch_to_tsquery(language, query)
        rank = func.ts_rank_cd(vector, ts_query).label("score")
        statement = (
            select(DocumentPage, rank)
            .join(
                Document,
                (Document.id == DocumentPage.document_id)
                & (Document.organization_id == DocumentPage.organization_id),
            )
            .where(
                DocumentPage.organization_id == self.tenant.organization_id,
                Document.deleted_at.is_(None),
                vector.op("@@")(ts_query),
            )
            .order_by(rank.desc(), DocumentPage.page_number.asc())
            .limit(limit)
        )
        return [(row[0], float(row[1])) for row in self.session.execute(statement)]

    def _search_portable(
        self,
        query: str,
        *,
        limit: int,
    ) -> list[tuple[DocumentPage, float]]:
        tokens = _search_tokens(query)
        lowered_text = func.lower(DocumentPage.text_content)
        statement = (
            select(DocumentPage)
            .join(
                Document,
                (Document.id == DocumentPage.document_id)
                & (Document.organization_id == DocumentPage.organization_id),
            )
            .where(
                DocumentPage.organization_id == self.tenant.organization_id,
                Document.deleted_at.is_(None),
                or_(*(lowered_text.contains(token) for token in tokens)),
            )
            .order_by(DocumentPage.created_at.desc(), DocumentPage.page_number.asc())
            .limit(250)
        )
        pages = list(self.session.scalars(statement))
        ranked = [
            (page, _portable_score(page.text_content, tokens))
            for page in pages
        ]
        ranked.sort(key=lambda item: (-item[1], item[0].page_number))
        return ranked[:limit]

    @staticmethod
    def _validate_pages(pages: Iterable[DocumentPageInput]) -> list[DocumentPageInput]:
        normalized = list(pages)
        page_numbers = [page.page_number for page in normalized]
        if any(number < 1 for number in page_numbers):
            raise ValueError("Page numbers must be positive.")
        if len(set(page_numbers)) != len(page_numbers):
            raise ValueError("Page numbers must be unique within a document.")
        if any(len(page.extraction_method) > 20 or not page.extraction_method for page in normalized):
            raise ValueError("Each page requires a valid extraction method.")
        return sorted(normalized, key=lambda page: page.page_number)


def _search_tokens(query: str) -> tuple[str, ...]:
    tokens = tuple(dict.fromkeys(re.findall(r"[a-z0-9]+", query.lower())))
    return tokens or (query.lower(),)


def _portable_score(text: str, tokens: tuple[str, ...]) -> float:
    lowered = text.lower()
    return sum(lowered.count(token) for token in tokens) / max(len(tokens), 1)


def _build_excerpt(text: str, query: str, *, radius: int = 110) -> str:
    compact = " ".join(text.split())
    if not compact:
        return ""
    lowered = compact.lower()
    positions = [lowered.find(token) for token in _search_tokens(query)]
    matches = [position for position in positions if position >= 0]
    center = min(matches) if matches else 0
    start = max(center - radius, 0)
    end = min(center + radius, len(compact))
    excerpt = compact[start:end]
    if start:
        excerpt = f"...{excerpt}"
    if end < len(compact):
        excerpt = f"{excerpt}..."
    return excerpt
