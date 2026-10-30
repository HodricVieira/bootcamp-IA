import fitz
import pytest

from app.services.pdf_reader import (
    PDFReaderError,
    PDFTooManyPagesError,
    _normalize_text,
    extract_text,
)


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


def test_rejects_pdf_above_max_pages(pdf_bytes: bytes) -> None:
    with pytest.raises(PDFTooManyPagesError):
        extract_text(pdf_bytes, max_pages=1)
    assert extract_text(pdf_bytes, max_pages=2).pages == 2


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("7 dias\ncorridos", "7 dias corridos"),
        ("Escola Horizonte.\nO prazo", "Escola Horizonte. O prazo"),
        ("a\t\r\n b\x00c", "a bc"),
    ],
)
def test_normalize_text_keeps_words_separated_by_line_breaks(raw: str, expected: str) -> None:
    assert _normalize_text(raw) == expected
