from dataclasses import dataclass

import re
import unicodedata

import fitz


class PDFReaderError(ValueError):
    """Indica que os bytes não representam um PDF legível."""


class PDFTooManyPagesError(PDFReaderError):
    """Indica que o PDF ultrapassa o limite de páginas permitido."""


class PDFPasswordError(PDFReaderError):
    """Indica que o PDF exige senha para leitura."""


@dataclass(frozen=True)
class PageText:
    page: int
    text: str


@dataclass(frozen=True)
class ExtractionResult:
    pages: int
    characters: int
    page_texts: list[PageText]

    @property
    def has_text(self) -> bool:
        return bool(self.characters)


def extract_text(pdf_bytes: bytes, max_pages: int | None = None) -> ExtractionResult:
    if not pdf_bytes:
        raise PDFReaderError("O arquivo está vazio.")

    try:
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
    except (fitz.FileDataError, RuntimeError) as exc:
        raise PDFReaderError("O arquivo não é um PDF válido.") from exc

    try:
        if document.needs_pass:
            raise PDFPasswordError("O documento PDF está protegido por senha.")
        if max_pages is not None and document.page_count > max_pages:
            raise PDFTooManyPagesError(f"O documento excede o limite de {max_pages} páginas.")
        page_texts = [
            PageText(page=number, text=_normalize_text(page.get_text("text")))
            for number, page in enumerate(document, start=1)
        ]
        characters = sum(len(item.text) for item in page_texts)
        return ExtractionResult(
            pages=document.page_count,
            characters=characters,
            page_texts=page_texts,
        )
    except PDFReaderError:
        raise
    except (RuntimeError, ValueError) as exc:
        raise PDFReaderError("Não foi possível extrair o texto do PDF.") from exc
    finally:
        document.close()


_CONTROL_OR_WHITESPACE = re.compile(r"\s+", re.UNICODE)


def _normalize_text(text: str) -> str:
    without_controls = "".join(
        character for character in text if not unicodedata.category(character).startswith("C")
    )
    return _CONTROL_OR_WHITESPACE.sub(" ", without_controls).strip()
