import hashlib
import json
import re

import fitz
import pytest

from app.main import app
from app.services.ai_service import get_answerer
from app.services.document_store import ScoredChunk, document_store
from app.services.embeddings import get_embedder, normalize

_WORD_PATTERN = re.compile(r"[^\W_]+", re.UNICODE)


class FakeEmbedder:
    """Embedder determinístico e sem rede: saco de palavras projetado por hash."""

    def __init__(self, dimensions: int = 768) -> None:
        self.dimensions = dimensions

    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for word in _WORD_PATTERN.findall(text.casefold()):
            digest = hashlib.sha256(word.encode("utf-8")).digest()
            vector[int.from_bytes(digest[:4], "big") % self.dimensions] += 1.0
        if not any(vector):
            vector[0] = 1.0
        return normalize(vector)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


class FakeAnswerer:
    """Answerer sem rede: devolve uma resposta pré-definida e registra as chamadas."""

    def __init__(self, response: str | Exception | None = None) -> None:
        self.response = response
        self.calls: list[tuple[str, list[ScoredChunk]]] = []

    def generate(self, question: str, chunks: list[ScoredChunk]) -> str:
        self.calls.append((question, chunks))
        if isinstance(self.response, Exception):
            raise self.response
        if self.response is not None:
            return self.response
        return json.dumps(
            {
                "found": True,
                "answer": f"Segundo o documento: {chunks[0].text} [1]",
                "citations": [{"ref": 1, "quote": chunks[0].text[:200]}],
            }
        )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "integration: chama o Gemini real (requer chave)")


@pytest.fixture(autouse=True)
def clear_store():
    document_store._documents.clear()
    yield
    document_store._documents.clear()


@pytest.fixture(autouse=True)
def fake_embedder():
    embedder = FakeEmbedder()
    app.dependency_overrides[get_embedder] = lambda: embedder
    yield embedder
    app.dependency_overrides.pop(get_embedder, None)


@pytest.fixture(autouse=True)
def fake_answerer():
    answerer = FakeAnswerer()
    app.dependency_overrides[get_answerer] = lambda: answerer
    yield answerer
    app.dependency_overrides.pop(get_answerer, None)


@pytest.fixture
def pdf_bytes() -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "O prazo para matrícula é 15 de fevereiro.")
    page = document.new_page()
    page.insert_text((72, 72), "Documentos necessários para a matrícula.")
    data = document.tobytes()
    document.close()
    return data
