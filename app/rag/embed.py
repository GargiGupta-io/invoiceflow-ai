"""Build and persist a deterministic knowledge index for retrieval."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .chunker import KnowledgeChunk, chunk_markdown_file


@dataclass(slots=True)
class KnowledgeIndex:
    """A lightweight lexical index over finance KB chunks."""

    chunks: list[KnowledgeChunk]
    token_to_chunk_ids: dict[str, list[str]] = field(default_factory=dict)
    chunk_lookup: dict[str, KnowledgeChunk] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "chunks": [chunk.to_dict() for chunk in self.chunks],
            "token_to_chunk_ids": self.token_to_chunk_ids,
        }


def build_knowledge_index(kb_dir: str | Path) -> KnowledgeIndex:
    """Read all KB markdown files and build a retrieval-ready index."""

    kb_path = Path(kb_dir).expanduser().resolve()
    markdown_files = sorted(
        path
        for path in kb_path.glob("*.md")
        if path.name.lower() not in {"readme.md"}
    )

    chunks: list[KnowledgeChunk] = []
    for markdown_file in markdown_files:
        chunks.extend(chunk_markdown_file(markdown_file))

    token_to_chunk_ids: dict[str, list[str]] = {}
    chunk_lookup: dict[str, KnowledgeChunk] = {}

    for chunk in chunks:
        chunk_lookup[chunk.chunk_id] = chunk
        for token in chunk.tokens:
            token_to_chunk_ids.setdefault(token, []).append(chunk.chunk_id)

    return KnowledgeIndex(
        chunks=chunks,
        token_to_chunk_ids=token_to_chunk_ids,
        chunk_lookup=chunk_lookup,
    )


def save_knowledge_index(index: KnowledgeIndex, output_path: str | Path) -> Path:
    """Persist the built index to JSON for reuse."""

    destination = Path(output_path).expanduser().resolve()
    destination.write_text(
        json.dumps(index.to_dict(), indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    return destination


def load_knowledge_index(path: str | Path) -> KnowledgeIndex:
    """Load a previously saved knowledge index from JSON."""

    source_path = Path(path).expanduser().resolve()
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    chunks = [KnowledgeChunk(**item) for item in payload.get("chunks", [])]
    token_to_chunk_ids = payload.get("token_to_chunk_ids", {})
    chunk_lookup = {chunk.chunk_id: chunk for chunk in chunks}
    return KnowledgeIndex(
        chunks=chunks,
        token_to_chunk_ids=token_to_chunk_ids,
        chunk_lookup=chunk_lookup,
    )
