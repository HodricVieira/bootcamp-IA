import math
from functools import lru_cache
from typing import Any, Protocol

from app.core.config import settings

BATCH_SIZE = 100


class EmbeddingError(RuntimeError):
    """Indica que não foi possível gerar os embeddings."""


class Embedder(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


def normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        raise EmbeddingError("O embedding retornado é um vetor nulo.")
    return [value / norm for value in vector]


class GeminiEmbedder:
    def __init__(self, api_key: str, model: str, dimensions: int, client: Any = None) -> None:
        self._api_key = api_key
        self._model = model
        self._dimensions = dimensions
        self._client = client

    def _get_client(self) -> Any:
        if self._client is None:
            if not self._api_key:
                raise EmbeddingError("DOCUMIND_GEMINI_API_KEY não configurada.")
            from google import genai

            self._client = genai.Client(api_key=self._api_key)
        return self._client

    def _embed(self, texts: list[str], task_type: str) -> list[list[float]]:
        from google.genai import types

        client = self._get_client()
        config = types.EmbedContentConfig(
            task_type=task_type, output_dimensionality=self._dimensions
        )
        vectors: list[list[float]] = []
        for start in range(0, len(texts), BATCH_SIZE):
            batch = texts[start : start + BATCH_SIZE]
            try:
                response = client.models.embed_content(
                    model=self._model, contents=batch, config=config
                )
            except Exception as exc:
                raise EmbeddingError("Falha ao gerar embeddings no Gemini.") from exc
            embeddings = response.embeddings or []
            if len(embeddings) != len(batch):
                raise EmbeddingError("O Gemini retornou uma quantidade inesperada de embeddings.")
            for embedding in embeddings:
                values = list(embedding.values or [])
                if len(values) != self._dimensions:
                    raise EmbeddingError("O Gemini retornou um embedding com dimensão inesperada.")
                vectors.append(normalize(values))
        return vectors

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self._embed(texts, "RETRIEVAL_DOCUMENT")

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], "RETRIEVAL_QUERY")[0]


@lru_cache
def get_embedder() -> Embedder:
    return GeminiEmbedder(
        api_key=settings.gemini_api_key,
        model=settings.gemini_embed_model,
        dimensions=settings.embed_dim,
    )
