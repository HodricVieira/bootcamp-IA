import fitz
import pytest

from app.services.pdf_reader import PDFReaderError, extract_text


def test_extract_text_preserves_pages(pdf_bytes: bytes) -> None:
    result = extract_text(pdf_bytes)
    assert result.pages == 2
    assert result.page_texts[0].page == 1
    assert "15 de fevereiro" in result.page_texts[0].text


def test_rejects_invalid_pdf() -> None:
    with pytest.raises(PDFReaderError):
        extract_text(b"not a pdf")


def test_detects_pdf_without_text() -> None:
    document = fitz.open()
    document.new_page()
    data = document.tobytes()
    document.close()
    assert not extract_text(data).has_text
