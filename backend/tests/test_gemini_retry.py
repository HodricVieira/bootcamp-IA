import json
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient
from google.genai import errors

from app.main import app
from app.services.ai_service import AIRateLimitError, AIServiceError, GeminiAnswerer, get_answerer
from app.services.document_store import ScoredChunk
from app.services.embeddings import EmbeddingError, EmbeddingRateLimitError, GeminiEmbedder
from app.services.gemini_retry import is_transient

client = TestClient(app)

CHUNKS = [ScoredChunk(page=1, chunk_index=0, text="O prazo é 15 de fevereiro.", score=0.9)]
ANSWER = json.dumps(
    {"found": True, "answer": "O prazo é 15 de fevereiro [1].",
     "citations": [{"ref": 1, "quote": "15 de fevereiro"}]}
)


def api_error(code: int) -> errors.APIError:
    status = {400: "INVALID_ARGUMENT", 429: "RESOURCE_EXHAUSTED", 503: "UNAVAILABLE"}[code]
    body = {"error": {"code": code, "message": "erro", "status": status}}
    return errors.ClientError(code, body) if code < 500 else errors.ServerError(code, body)


class FakeModels:
    """Falha com os erros da lista, em ordem, e depois responde."""

    def __init__(self, failures: list[Exception]) -> None:
        self.failures = failures
        self.calls = 0

    def _next(self):
        self.calls += 1
        if self.failures:
            raise self.failures.pop(0)

    def embed_content(self, *, model, contents, config):
        self._next()
        return SimpleNamespace(embeddings=[SimpleNamespace(values=[1.0] * 4) for _ in contents])

    def generate_content(self, *, model, contents, config):
        self._next()
        return SimpleNamespace(text=ANSWER)


def make(failures: list[Exception]):
    models = FakeModels(failures)
    sleeps: list[float] = []
    fake_client = SimpleNamespace(models=models)
    embedder = GeminiEmbedder("chave", "modelo", 4, client=fake_client, sleep=sleeps.append)
    answerer = GeminiAnswerer("chave", "modelo", client=fake_client, sleep=sleeps.append)
    return embedder, answerer, models, sleeps


def test_fails_once_then_answers() -> None:
    embedder, answerer, models, sleeps = make([api_error(503)])
    assert len(embedder.embed_query("pergunta")) == 4
    assert models.calls == 2
    assert sleeps == [1.0]

    models.failures = [api_error(503)]
    assert answerer.generate("Qual o prazo?", CHUNKS) == ANSWER
    assert models.calls == 4
    assert sleeps == [1.0, 1.0]


def test_always_429_retries_twice_then_raises_rate_limit() -> None:
    embedder, answerer, models, sleeps = make([api_error(429) for _ in range(3)])
    with pytest.raises(EmbeddingRateLimitError):
        embedder.embed_query("pergunta")
    assert models.calls == 3
    assert sleeps == [1.0, 2.0]

    models.failures = [api_error(429) for _ in range(3)]
    with pytest.raises(AIRateLimitError):
        answerer.generate("Qual o prazo?", CHUNKS)
    assert models.calls == 6


def test_invalid_key_fails_without_retry() -> None:
    embedder, answerer, models, sleeps = make([api_error(400)])
    with pytest.raises(EmbeddingError) as embed_exc:
        embedder.embed_query("pergunta")
    assert not isinstance(embed_exc.value, EmbeddingRateLimitError)

    models.failures = [api_error(400)]
    with pytest.raises(AIServiceError) as answer_exc:
        answerer.generate("Qual o prazo?", CHUNKS)
    assert not isinstance(answer_exc.value, AIRateLimitError)
    assert models.calls == 2
    assert sleeps == []


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (api_error(503), True),
        (api_error(429), True),
        (httpx.ReadTimeout("timeout"), True),
        (TimeoutError(), True),
        (httpx.ConnectError("conexão recusada"), True),
        (api_error(400), False),
        (RuntimeError("outro"), False),
    ],
)
def test_transient_classification(exc: Exception, expected: bool) -> None:
    assert is_transient(exc) is expected


def test_api_returns_429_when_gemini_stays_rate_limited(pdf_bytes: bytes) -> None:
    _, answerer, _, _ = make([api_error(429) for _ in range(3)])
    app.dependency_overrides[get_answerer] = lambda: answerer
    upload = client.post(
        "/documents/upload", files={"file": ("doc.pdf", pdf_bytes, "application/pdf")}
    )
    assert upload.status_code == 201
    response = client.post(
        f"/documents/{upload.json()['document_id']}/ask",
        json={"question": "Qual o prazo para matrícula?"},
    )
    assert response.status_code == 429
    assert response.json() == {
        "detail": {
            "code": "RATE_LIMITED",
            "message": "Limite de uso da IA atingido. Aguarde um minuto e tente de novo.",
        }
    }
