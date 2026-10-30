import math

import pytest

from app.services.embeddings import EmbeddingError, NomicEmbedder


class FakeModel:
    def __init__(self, dimensions: int, error: Exception | None = None) -> None:
        self.dimensions = dimensions
        self.error = error
        self.calls: list[dict] = []

    def encode(self, texts, **kwargs):
        self.calls.append({"texts": texts, **kwargs})
        if self.error:
            raise self.error
        return [[3.0] * self.dimensions for _ in texts]


def make_embedder(dimensions: int = 4, error: Exception | None = None):
    model = FakeModel(dimensions, error)
    return NomicEmbedder(dimensions=dimensions, model=model), model


def test_documents_are_batched_prefixed_and_normalized() -> None:
    embedder, model = make_embedder()
    vectors = embedder.embed_documents([f"trecho {i}" for i in range(250)])
    assert [len(call["texts"]) for call in model.calls] == [100, 100, 50]
    assert all(
        text.startswith("search_document: ")
        for call in model.calls
        for text in call["texts"]
    )
    assert all(call["convert_to_numpy"] for call in model.calls)
    assert len(vectors) == 250
    assert math.sqrt(sum(value * value for value in vectors[0])) == pytest.approx(1.0)


def test_query_uses_query_prefix() -> None:
    embedder, model = make_embedder()
    vector = embedder.embed_query("pergunta")
    assert model.calls[0]["texts"] == ["search_query: pergunta"]
    assert len(vector) == 4


def test_empty_documents_do_not_call_model() -> None:
    embedder, model = make_embedder()
    assert embedder.embed_documents([]) == []
    assert model.calls == []


def test_model_errors_become_embedding_error() -> None:
    embedder, _ = make_embedder(error=RuntimeError("falha simulada"))
    with pytest.raises(EmbeddingError, match="Falha ao gerar embeddings"):
        embedder.embed_query("pergunta")


def test_unexpected_embedding_dimensions_raise_error() -> None:
    embedder = NomicEmbedder(dimensions=5, model=FakeModel(dimensions=4))
    with pytest.raises(EmbeddingError, match="dimensão inesperada"):
        embedder.embed_query("pergunta")


def test_unexpected_embedding_count_raises_error() -> None:
    class WrongCountModel:
        def encode(self, texts, **kwargs):
            return []

    embedder = NomicEmbedder(model=WrongCountModel())
    with pytest.raises(EmbeddingError, match="quantidade inesperada"):
        embedder.embed_query("pergunta")
