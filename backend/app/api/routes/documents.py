import logging
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.core.config import settings
from app.schemas.document import (
    DocumentMetadata,
    DocumentUploadResponse,
    QuestionRequest,
    QuestionResponse,
    SourceExcerpt,
)
from app.services.ai_service import generate_answer
from app.services.document_search import search_chunks
from app.services.document_store import document_store
from app.services.pdf_reader import PDFReaderError, extract_text

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])


def _parse_id(document_id: str) -> UUID:
    try:
        return UUID(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Documento não encontrado.") from exc


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...)) -> DocumentUploadResponse:
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
    try:
        extraction = extract_text(bytes(content))
    except PDFReaderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not extraction.has_text:
        raise HTTPException(status_code=400, detail="O documento não contém texto pesquisável.")
    document = document_store.add(
        filename=file.filename,
        pages=extraction.pages,
        characters=extraction.characters,
        page_texts=extraction.page_texts,
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
def ask_document(document_id: str, request: QuestionRequest) -> QuestionResponse:
    document = document_store.get(_parse_id(document_id))
    if document is None:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="A pergunta não pode estar vazia.")
    chunks = search_chunks(
        document.page_texts,
        question,
        chunk_size=settings.chunk_size,
        overlap=settings.chunk_overlap,
        limit=settings.max_search_results,
    )
    return QuestionResponse(
        document_id=str(document.document_id),
        question=question,
        answer=generate_answer(question, chunks),
        sources=[SourceExcerpt(page=chunk.page, text=chunk.text) for chunk in chunks],
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: str) -> None:
    if not document_store.delete(_parse_id(document_id)):
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
