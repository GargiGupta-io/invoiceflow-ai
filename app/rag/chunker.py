"""Chunk markdown knowledge-base files into retrieval-ready sections."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path

SECTION_CODE_RE = re.compile(r"\b[A-Z]{2,}(?:-[A-Z0-9]+)+\b")
TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass(slots=True)
class KnowledgeChunk:
    """One grounded, citeable section from the finance knowledge base."""

    chunk_id: str
    section_code: str
    source_file: str
    source_title: str
    section_title: str
    text: str
    tokens: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def chunk_markdown_file(path: str | Path) -> list[KnowledgeChunk]:
    """Split a markdown KB file into section-sized chunks."""

    source_path = Path(path).expanduser().resolve()
    raw_text = source_path.read_text(encoding="utf-8")
    lines = raw_text.splitlines()

    source_title = source_path.stem.replace("_", " ").title()
    current_heading: str | None = None
    current_lines: list[str] = []
    chunks: list[KnowledgeChunk] = []

    for line in lines:
        if line.startswith("# "):
            source_title = line[2:].strip() or source_title
            continue
        if line.startswith("## "):
            if current_heading is not None:
                chunk = _build_chunk(
                    source_file=source_path.name,
                    source_title=source_title,
                    section_title=current_heading,
                    body_lines=current_lines,
                )
                if chunk is not None:
                    chunks.append(chunk)
            current_heading = line[3:].strip()
            current_lines = []
            continue
        if current_heading is not None:
            current_lines.append(line)

    if current_heading is not None:
        chunk = _build_chunk(
            source_file=source_path.name,
            source_title=source_title,
            section_title=current_heading,
            body_lines=current_lines,
        )
        if chunk is not None:
            chunks.append(chunk)

    return chunks


def _build_chunk(
    source_file: str,
    source_title: str,
    section_title: str,
    body_lines: list[str],
) -> KnowledgeChunk | None:
    text = _normalize_body(body_lines)
    if not text:
        return None

    section_code = _extract_section_code(section_title)
    chunk_id = section_code if section_code != "section" else _slugify(section_title)
    tokens = _tokenize(f"{section_title}\n{text}")

    return KnowledgeChunk(
        chunk_id=chunk_id,
        section_code=section_code,
        source_file=source_file,
        source_title=source_title,
        section_title=section_title,
        text=text,
        tokens=tokens,
    )


def _normalize_body(lines: list[str]) -> str:
    cleaned_lines: list[str] = []
    blank_streak = 0
    for line in lines:
        stripped = line.rstrip()
        if stripped:
            cleaned_lines.append(stripped)
            blank_streak = 0
            continue
        blank_streak += 1
        if blank_streak <= 1:
            cleaned_lines.append("")
    return "\n".join(cleaned_lines).strip()


def _extract_section_code(section_title: str) -> str:
    match = SECTION_CODE_RE.search(section_title)
    if match is None:
        return "section"
    return match.group(0)


def _slugify(value: str) -> str:
    text = value.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "section"


def _tokenize(text: str) -> list[str]:
    tokens = TOKEN_RE.findall(text.lower())
    seen: set[str] = set()
    ordered: list[str] = []
    for token in tokens:
        if len(token) <= 1 or token in seen:
            continue
        ordered.append(token)
        seen.add(token)
    return ordered
