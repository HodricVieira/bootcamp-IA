import math
from functools import lru_cache
from typing import Any, Protocol

MODEL_NAME = "nomic-ai/nomic-embed-text-v1.5"
EMBEDDING_DIMENSIONS = 768
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


class NomicEmbedder:
    def __init__(
        self,
        model_name: str = MODEL_NAME,
        dimensions: int = EMBEDDING_DIMENSIONS,
        model: Any = None,
    ) -> None:
        self._model_name = model_name
        self._dimensions = dimensions
        self._model = model

    def _get_model(self) -> Any:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise EmbeddingError(
                    "A dependência sentence-transformers não está instalada."
                ) from exc
            try:
                self._model = SentenceTransformer(self._model_name)
            except Exception as exc:
                raise EmbeddingError("Falha ao carregar o modelo Nomic.") from exc
        return self._model

    def _embed(self, texts: list[str], task: str) -> list[list[float]]:
        model = self._get_model()
        vectors: list[list[float]] = []
        for start in range(0, len(texts), BATCH_SIZE):
            batch = texts[start : start + BATCH_SIZE]
            try:
                encoded = model.encode(
                    [f"{task}: {text}" for text in batch],
                    batch_size=BATCH_SIZE,
                    convert_to_numpy=True,
                    show_progress_bar=False,
                )
            except Exception as exc:
                raise EmbeddingError("Falha ao gerar embeddings com o Nomic.") from exc
            rows = encoded.tolist() if hasattr(encoded, "tolist") else encoded
            if len(rows) != len(batch):
                raise EmbeddingError(
                    "O Nomic retornou uma quantidade inesperada de embeddings."
                )
            for row in rows:
                values = [float(value) for value in row]
                if len(values) != self._dimensions:
                    raise EmbeddingError(
                        "O Nomic retornou um embedding com dimensão inesperada."
                    )
                vectors.append(normalize(values))
        return vectors

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self._embed(texts, "search_document")

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], "search_query")[0]


@lru_cache
def get_embedder() -> Embedder:
    return NomicEmbedder()
