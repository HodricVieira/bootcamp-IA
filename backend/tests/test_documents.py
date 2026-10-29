from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def upload(pdf_bytes: bytes) -> dict:
    return client.post(
        "/documents/upload",
        files={"file": ("regulamento.pdf", pdf_bytes, "application/pdf")},
    ).json()


def test_upload_metadata_and_question(pdf_bytes: bytes) -> None:
    uploaded = upload(pdf_bytes)
    assert uploaded["status"] == "processed"
    document_id = uploaded["document_id"]
    metadata = client.get(f"/documents/{document_id}")
    assert metadata.status_code == 200
    assert "characters" in metadata.json()
    answer = client.post(
        f"/documents/{document_id}/ask", json={"question": "Qual o prazo da matrícula?"}
    )
    assert answer.status_code == 200
    assert answer.json()["sources"][0]["page"] == 1


def test_invalid_upload_and_empty_pdf(pdf_bytes: bytes) -> None:
    assert client.post(
        "/documents/upload",
        files={"file": ("arquivo.pdf", b"texto", "application/pdf")},
    ).status_code == 400
    import fitz

    document = fitz.open()
    document.new_page()
    empty_pdf = document.tobytes()
    document.close()
    assert client.post(
        "/documents/upload",
        files={"file": ("imagem.pdf", empty_pdf, "application/pdf")},
    ).status_code == 400


def test_missing_document_and_empty_question() -> None:
    assert client.get("/documents/00000000-0000-0000-0000-000000000000").status_code == 404
    assert client.post(
        "/documents/00000000-0000-0000-0000-000000000000/ask", json={"question": " "}
    ).status_code == 404


def test_delete_document(pdf_bytes: bytes) -> None:
    document_id = upload(pdf_bytes)["document_id"]
    assert client.delete(f"/documents/{document_id}").status_code == 204
    assert client.get(f"/documents/{document_id}").status_code == 404
