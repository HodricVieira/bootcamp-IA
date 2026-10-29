import fitz
from fastapi.testclient import TestClient

from app.main import app
from app.services.embeddings import EmbeddingError, get_embedder

client = TestClient(app)


def upload(pdf_bytes: bytes) -> dict:
    return client.post(
        "/documents/upload",
        files={"file": ("regulamento.pdf", pdf_bytes, "application/pdf")},
    ).json()


class FailingEmbedder:
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise EmbeddingError("falha simulada")

    def embed_query(self, text: str) -> list[float]:
        raise EmbeddingError("falha simulada")


def test_upload_metadata_and_question(pdf_bytes: bytes) -> None:
    uploaded = upload(pdf_bytes)
    assert uploaded["status"] == "processed"
    document_id = uploaded["document_id"]
    metadata = client.get(f"/documents/{document_id}")
    assert metadata.status_code == 200
    assert "characters" in metadata.json()
    answer = client.post(
        f"/documents/{document_id}/ask", json={"question": "Qual o prazo para matrícula?"}
    )
    assert answer.status_code == 200
    sources = answer.json()["sources"]
    assert [source["page"] for source in sources] == [1]
    assert "15 de fevereiro" in sources[0]["text"]


def test_question_without_similar_chunks_returns_no_sources(pdf_bytes: bytes) -> None:
    document_id = upload(pdf_bytes)["document_id"]
    answer = client.post(f"/documents/{document_id}/ask", json={"question": "Qual a cor do céu?"})
    assert answer.status_code == 200
    assert answer.json()["sources"] == []


def test_upload_embeds_chunks_once(pdf_bytes: bytes, fake_embedder) -> None:
    calls: list[int] = []
    original = fake_embedder.embed_documents
    fake_embedder.embed_documents = lambda texts: calls.append(len(texts)) or original(texts)
    document_id = upload(pdf_bytes)["document_id"]
    for _ in range(2):
        client.post(f"/documents/{document_id}/ask", json={"question": "prazo"})
    assert calls == [2]


def test_invalid_upload_and_empty_pdf(pdf_bytes: bytes) -> None:
    assert client.post(
        "/documents/upload",
        files={"file": ("arquivo.pdf", b"", "application/pdf")},
    ).status_code == 400
    assert client.post(
        "/documents/upload",
        files={"file": ("arquivo.pdf", b"%PDF-1.7 corrompido", "application/pdf")},
    ).status_code == 400
    document = fitz.open()
    document.new_page()
    empty_pdf = document.tobytes()
    document.close()
    assert client.post(
        "/documents/upload",
        files={"file": ("imagem.pdf", empty_pdf, "application/pdf")},
    ).status_code == 400


def test_rejects_non_pdf_signature() -> None:
    response = client.post(
        "/documents/upload",
        files={"file": ("arquivo.pdf", b"texto qualquer", "application/pdf")},
    )
    assert response.status_code == 415


def test_rejects_pdf_above_page_limit() -> None:
    document = fitz.open()
    for _ in range(101):
        document.new_page().insert_text((72, 72), "Página de teste.")
    data = document.tobytes()
    document.close()
    response = client.post(
        "/documents/upload",
        files={"file": ("longo.pdf", data, "application/pdf")},
    )
    assert response.status_code == 413


def test_embedding_failure_returns_502(pdf_bytes: bytes) -> None:
    document_id = upload(pdf_bytes)["document_id"]
    app.dependency_overrides[get_embedder] = lambda: FailingEmbedder()
    expected = "O serviço de IA não respondeu. Tente de novo."
    response = client.post(f"/documents/{document_id}/ask", json={"question": "prazo"})
    assert response.status_code == 502
    assert response.json()["detail"] == expected
    response = client.post(
        "/documents/upload",
        files={"file": ("regulamento.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 502
    assert response.json()["detail"] == expected


def test_missing_document_and_empty_question() -> None:
    assert client.get("/documents/00000000-0000-0000-0000-000000000000").status_code == 404
    assert client.post(
        "/documents/00000000-0000-0000-0000-000000000000/ask", json={"question": " "}
    ).status_code == 404


def test_delete_document(pdf_bytes: bytes) -> None:
    document_id = upload(pdf_bytes)["document_id"]
    assert client.delete(f"/documents/{document_id}").status_code == 204
    assert client.get(f"/documents/{document_id}").status_code == 404
