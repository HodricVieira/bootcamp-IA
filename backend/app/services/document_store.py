import math
from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True)
class StoredChunk:
    page: int
    chunk_index: int
    text: str
    embedding: list[float]


@dataclass(frozen=True)
class ScoredChunk:
    page: int
    chunk_index: int
    text: str
    score: float


@dataclass(frozen=True)
class StoredDocument:
    document_id: UUID
    filename: str
    pages: int
    characters: int
    chunks: list[StoredChunk]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("Os vetores precisam ter a mesma dimensão.")
    norm = math.sqrt(sum(value * value for value in left)) * math.sqrt(
        sum(value * value for value in right)
    )
    if norm == 0:
        return 0.0
    return sum(a * b for a, b in zip(left, right)) / norm


def rank_by_similarity(
    chunks: list[StoredChunk],
    query_embedding: list[float],
    limit: int,
    min_similarity: float,
) -> list[ScoredChunk]:
    scored = [
        ScoredChunk(
            page=chunk.page,
            chunk_index=chunk.chunk_index,
            text=chunk.text,
            score=cosine_similarity(chunk.embedding, query_embedding),
        )
        for chunk in chunks
    ]
    relevant = [chunk for chunk in scored if chunk.score >= min_similarity]
    relevant.sort(key=lambda chunk: (-chunk.score, chunk.chunk_index))
    return relevant[:limit]


class DocumentStore:
    """Armazenamento temporário em memória, substituível por um repositório persistente."""

    def __init__(self) -> None:
        self._documents: dict[UUID, StoredDocument] = {}

    def add(
        self,
        filename: str,
        pages: int,
        characters: int,
        chunks: list[StoredChunk],
    ) -> StoredDocument:
        document = StoredDocument(
            document_id=uuid4(),
            filename=filename,
            pages=pages,
            characters=characters,
            chunks=chunks,
        )
        self._documents[document.document_id] = document
        return document

    def get(self, document_id: UUID) -> StoredDocument | None:
        return self._documents.get(document_id)

    def search(
        self,
        document_id: UUID,
        query_embedding: list[float],
        limit: int,
        min_similarity: float,
    ) -> list[ScoredChunk]:
        document = self._documents.get(document_id)
        if document is None:
            return []
        return rank_by_similarity(document.chunks, query_embedding, limit, min_similarity)

    def delete(self, document_id: UUID) -> bool:
        return self._documents.pop(document_id, None) is not None


document_store = DocumentStore()
