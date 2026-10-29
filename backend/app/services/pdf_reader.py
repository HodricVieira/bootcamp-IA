from dataclasses import dataclass

import fitz


class PDFReaderError(ValueError):
    """Indica que os bytes não representam um PDF legível."""


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


def extract_text(pdf_bytes: bytes) -> ExtractionResult:
    if not pdf_bytes:
        raise PDFReaderError("O arquivo está vazio.")

    try:
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
    except (fitz.FileDataError, RuntimeError) as exc:
        raise PDFReaderError("O arquivo não é um PDF válido.") from exc

    try:
        page_texts = [
            PageText(page=number, text=page.get_text("text").strip())
            for number, page in enumerate(document, start=1)
        ]
        characters = sum(len(item.text) for item in page_texts)
        return ExtractionResult(
            pages=document.page_count,
            characters=characters,
            page_texts=page_texts,
        )
    except (RuntimeError, ValueError) as exc:
        raise PDFReaderError("Não foi possível extrair o texto do PDF.") from exc
    finally:
        document.close()
