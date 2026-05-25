"""Knowledge-base chunking and indexing helpers."""

from .chunker import KnowledgeChunk, chunk_markdown_file
from .embed import KnowledgeIndex, build_knowledge_index, load_knowledge_index, save_knowledge_index
from .retrieve import RetrievalHit, hits_to_evidence_payloads, query_knowledge_index
from .self_heal import RetrievalRepairReport, repair_retrieval_if_needed

__all__ = [
    "KnowledgeChunk",
    "KnowledgeIndex",
    "RetrievalHit",
    "RetrievalRepairReport",
    "build_knowledge_index",
    "chunk_markdown_file",
    "hits_to_evidence_payloads",
    "load_knowledge_index",
    "query_knowledge_index",
    "repair_retrieval_if_needed",
    "save_knowledge_index",
]
