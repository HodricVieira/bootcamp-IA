import pytest

from app.services.document_search import split_into_chunks
from app.services.document_store import StoredChunk, cosine_similarity, rank_by_similarity
from app.services.pdf_reader import PageText


def test_chunks_preserve_pages_and_content() -> None:
    pages = [PageText(1, "um dois três quatro cinco"), PageText(2, "seis sete oito")]
    chunks = split_into_chunks(pages, chunk_size=12, overlap=2)
    assert [chunk.page for chunk in chunks].count(1) == 3
    assert [chunk.page for chunk in chunks][-1] == 2
    assert "um" in chunks[0].text
    assert "oito" in chunks[-1].text


def test_cosine_similarity() -> None:
    assert cosine_similarity([1.0, 0.0], [2.0, 0.0]) == pytest.approx(1.0)
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
    assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0


def test_rank_orders_by_score_limits_and_drops_below_threshold() -> None:
    chunks = [
        StoredChunk(page=1, chunk_index=0, text="baixo", embedding=[0.0, 1.0]),
        StoredChunk(page=1, chunk_index=1, text="médio", embedding=[0.8, 0.6]),
        StoredChunk(page=2, chunk_index=2, text="alto", embedding=[1.0, 0.0]),
        StoredChunk(page=3, chunk_index=3, text="alto também", embedding=[0.99, 0.14]),
    ]
    results = rank_by_similarity(chunks, [1.0, 0.0], limit=2, min_similarity=0.55)
    assert [result.text for result in results] == ["alto", "alto também"]
    assert results[0].score == pytest.approx(1.0)
    assert results[0].page == 2
    everything = rank_by_similarity(chunks, [1.0, 0.0], limit=10, min_similarity=0.55)
    assert "baixo" not in [result.text for result in everything]
    assert len(everything) == 3
