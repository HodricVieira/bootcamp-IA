from dataclasses import dataclass
from uuid import UUID, uuid4

from app.services.pdf_reader import PageText


@dataclass(frozen=True)
class StoredDocument:
    document_id: UUID
    filename: str
    pages: int
    characters: int
    page_texts: list[PageText]


class DocumentStore:
    """Armazenamento temporário em memória, substituível por um repositório persistente."""

    def __init__(self) -> None:
        self._documents: dict[UUID, StoredDocument] = {}

    def add(
        self,
        filename: str,
        pages: int,
        characters: int,
        page_texts: list[PageText],
    ) -> StoredDocument:
        document = StoredDocument(
            document_id=uuid4(),
            filename=filename,
            pages=pages,
            characters=characters,
            page_texts=page_texts,
        )
        self._documents[document.document_id] = document
        return document

    def get(self, document_id: UUID) -> StoredDocument | None:
        return self._documents.get(document_id)

    def delete(self, document_id: UUID) -> bool:
        return self._documents.pop(document_id, None) is not None


document_store = DocumentStore()
