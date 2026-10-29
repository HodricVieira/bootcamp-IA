import math
from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.services.embeddings import EmbeddingError, GeminiEmbedder


class FakeModels:
    def __init__(self, dimensions: int, error: Exception | None = None) -> None:
        self.dimensions = dimensions
        self.error = error
        self.calls: list[dict] = []

    def embed_content(self, *, model, contents, config):
        self.calls.append({"model": model, "size": len(contents), "config": config})
        if self.error:
            raise self.error
        return SimpleNamespace(
            embeddings=[SimpleNamespace(values=[3.0] * self.dimensions) for _ in contents]
        )


def make_embedder(dimensions: int = 4, error: Exception | None = None):
    models = FakeModels(dimensions, error)
    embedder = GeminiEmbedder("chave", "modelo", dimensions, client=SimpleNamespace(models=models))
    return embedder, models


def test_documents_are_batched_normalized_and_use_document_task() -> None:
    embedder, models = make_embedder()
    vectors = embedder.embed_documents([f"trecho {i}" for i in range(250)])
    assert [call["size"] for call in models.calls] == [100, 100, 50]
    assert all(call["config"].task_type == "RETRIEVAL_DOCUMENT" for call in models.calls)
    assert all(call["config"].output_dimensionality == 4 for call in models.calls)
    assert len(vectors) == 250
    assert math.sqrt(sum(v * v for v in vectors[0])) == pytest.approx(1.0)


def test_query_uses_query_task() -> None:
    embedder, models = make_embedder()
    vector = embedder.embed_query("pergunta")
    assert models.calls[0]["config"].task_type == "RETRIEVAL_QUERY"
    assert len(vector) == 4


def test_client_errors_become_embedding_error() -> None:
    embedder, _ = make_embedder(error=RuntimeError("rede"))
    with pytest.raises(EmbeddingError):
        embedder.embed_query("pergunta")


def test_missing_api_key_raises_embedding_error() -> None:
    with pytest.raises(EmbeddingError):
        GeminiEmbedder("", "modelo", 4).embed_query("pergunta")


@pytest.mark.integration
@pytest.mark.skipif(not settings.gemini_api_key, reason="DOCUMIND_GEMINI_API_KEY ausente")
def test_gemini_embedder_real() -> None:
    embedder = GeminiEmbedder(
        settings.gemini_api_key, settings.gemini_embed_model, settings.embed_dim
    )
    documents = embedder.embed_documents(
        ["O prazo para matrícula é 15 de fevereiro.", "A cantina abre às 7 horas."]
    )
    query = embedder.embed_query("Até quando posso fazer a matrícula?")
    assert len(query) == settings.embed_dim
    assert sum(a * b for a, b in zip(query, documents[0])) > sum(
        a * b for a, b in zip(query, documents[1])
    )
