import logging
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.config import settings
from app.schemas.document import (
    DocumentMetadata,
    DocumentUploadResponse,
    QuestionRequest,
    QuestionResponse,
    SourceExcerpt,
)
from app.services.ai_service import AIServiceError, Answerer, answer_question, get_answerer
from app.services.document_search import split_into_chunks
from app.services.document_store import StoredChunk, document_store
from app.services.embeddings import Embedder, EmbeddingError, get_embedder
from app.services.pdf_reader import PDFReaderError, PDFTooManyPagesError, extract_text

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])

AI_UNAVAILABLE = "O serviço de IA não respondeu. Tente de novo."


def _parse_id(document_id: str) -> UUID:
    try:
        return UUID(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Documento não encontrado.") from exc


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...), embedder: Embedder = Depends(get_embedder)
) -> DocumentUploadResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Arquivo não informado.")
    content = bytearray()
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        content.extend(chunk)
        if len(content) > settings.max_file_size:
            raise HTTPException(status_code=413, detail="O arquivo excede o limite de 10 MB.")
    if not content:
        raise HTTPException(status_code=400, detail="O arquivo está vazio.")
    if not content.startswith(b"%PDF"):
        raise HTTPException(status_code=415, detail="O arquivo enviado não é um PDF.")
    try:
        extraction = extract_text(bytes(content), max_pages=settings.max_pages)
    except PDFTooManyPagesError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except PDFReaderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not extraction.has_text:
        raise HTTPException(status_code=400, detail="O documento não contém texto pesquisável.")
    text_chunks = split_into_chunks(
        extraction.page_texts, settings.chunk_size, min(settings.chunk_overlap, settings.chunk_size - 1)
    )
    try:
        embeddings = embedder.embed_documents([chunk.text for chunk in text_chunks])
    except EmbeddingError as exc:
        logger.warning("Falha ao gerar embeddings do documento: %s", exc)
        raise HTTPException(status_code=502, detail=AI_UNAVAILABLE) from exc
    document = document_store.add(
        filename=file.filename,
        pages=extraction.pages,
        characters=extraction.characters,
        chunks=[
            StoredChunk(page=chunk.page, chunk_index=index, text=chunk.text, embedding=embedding)
            for index, (chunk, embedding) in enumerate(zip(text_chunks, embeddings))
        ],
    )
    return DocumentUploadResponse(
        document_id=str(document.document_id),
        filename=document.filename,
        pages=document.pages,
        characters=document.characters,
        status="processed",
    )


@router.get("/{document_id}", response_model=DocumentMetadata)
def get_document(document_id: str) -> DocumentMetadata:
    document = document_store.get(_parse_id(document_id))
    if document is None:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    return DocumentMetadata(
        document_id=str(document.document_id),
        filename=document.filename,
        pages=document.pages,
        characters=document.characters,
        status="processed",
    )


@router.post("/{document_id}/ask", response_model=QuestionResponse)
def ask_document(
    document_id: str,
    request: QuestionRequest,
    embedder: Embedder = Depends(get_embedder),
    answerer: Answerer = Depends(get_answerer),
) -> QuestionResponse:
    document = document_store.get(_parse_id(document_id))
    if document is None:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="A pergunta não pode estar vazia.")
    try:
        query_embedding = embedder.embed_query(question)
    except EmbeddingError as exc:
        logger.warning("Falha ao gerar embedding da pergunta: %s", exc)
        raise HTTPException(status_code=502, detail=AI_UNAVAILABLE) from exc
    chunks = document_store.search(
        document.document_id,
        query_embedding,
        limit=settings.max_search_results,
        min_similarity=settings.min_similarity,
    )
    try:
        result = answer_question(question, chunks, answerer)
    except AIServiceError as exc:
        logger.warning("Falha ao gerar a resposta: %s", exc)
        raise HTTPException(status_code=502, detail=AI_UNAVAILABLE) from exc
    return QuestionResponse(
        document_id=str(document.document_id),
        question=question,
        found=result.found,
        answer=result.answer,
        sources=[
            SourceExcerpt(
                ref=item.ref, page=item.page, text=item.text, quote=item.quote, score=item.score
            )
            for item in result.citations
        ],
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: str) -> None:
    if not document_store.delete(_parse_id(document_id)):
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
