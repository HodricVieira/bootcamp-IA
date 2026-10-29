from dataclasses import dataclass

from app.services.pdf_reader import PageText


@dataclass(frozen=True)
class TextChunk:
    page: int
    text: str


def split_into_chunks(
    pages: list[PageText], chunk_size: int = 1000, overlap: int = 150
) -> list[TextChunk]:
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("chunk_size deve ser positivo e overlap menor que chunk_size.")

    chunks: list[TextChunk] = []
    for page in pages:
        words = page.text.split()
        if not words:
            continue
        current: list[str] = []
        current_length = 0
        for word in words:
            added_length = len(word) + (1 if current else 0)
            if current and current_length + added_length > chunk_size:
                chunks.append(TextChunk(page=page.page, text=" ".join(current)))
                overlap_words: list[str] = []
                overlap_length = 0
                for previous in reversed(current):
                    if overlap_length + len(previous) + 1 > overlap:
                        break
                    overlap_words.insert(0, previous)
                    overlap_length += len(previous) + 1
                current = overlap_words
                current_length = len(" ".join(current))
            current.append(word)
            current_length += added_length
        if current:
            chunks.append(TextChunk(page=page.page, text=" ".join(current)))
    return chunks

