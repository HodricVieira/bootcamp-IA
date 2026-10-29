from app.services.document_search import search_chunks, split_into_chunks
from app.services.pdf_reader import PageText


def test_chunks_preserve_pages_and_content() -> None:
    pages = [PageText(1, "um dois três quatro cinco"), PageText(2, "seis sete oito")]
    chunks = split_into_chunks(pages, chunk_size=12, overlap=2)
    assert [chunk.page for chunk in chunks].count(1) == 3
    assert [chunk.page for chunk in chunks][-1] == 2
    assert "um" in chunks[0].text
    assert "oito" in chunks[-1].text


def test_search_returns_only_matching_chunks() -> None:
    pages = [PageText(1, "prazo da matrícula quinze de fevereiro"), PageText(2, "endereço postal")]
    results = search_chunks(pages, "matrícula", chunk_size=100)
    assert len(results) == 1
    assert results[0].page == 1
