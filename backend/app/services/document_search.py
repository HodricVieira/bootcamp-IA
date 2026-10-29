import re
import unicodedata
from dataclasses import dataclass

from app.services.pdf_reader import PageText

_WORD_PATTERN = re.compile(r"[^\W_]+", re.UNICODE)


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


def _normalize(value: str) -> list[str]:
    without_accents = unicodedata.normalize("NFKD", value)
    plain = "".join(char for char in without_accents if not unicodedata.combining(char))
    return [word.casefold() for word in _WORD_PATTERN.findall(plain)]


def search_chunks(
    pages: list[PageText],
    question: str,
    chunk_size: int = 1000,
    overlap: int = 150,
    limit: int = 5,
) -> list[TextChunk]:
    keywords = set(_normalize(question))
    if not keywords:
        return []
    effective_overlap = min(overlap, chunk_size - 1)
    scored = [
        (sum(keyword in set(_normalize(chunk.text)) for keyword in keywords), index, chunk)
        for index, chunk in enumerate(
            split_into_chunks(pages, chunk_size, effective_overlap)
        )
    ]
    return [
        chunk for score, _, chunk in sorted(scored, key=lambda item: (-item[0], item[1]))[:limit]
        if score > 0
    ]
