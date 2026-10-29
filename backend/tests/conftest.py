import fitz
import pytest

from app.services.document_store import document_store


@pytest.fixture(autouse=True)
def clear_store():
    document_store._documents.clear()
    yield
    document_store._documents.clear()


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
