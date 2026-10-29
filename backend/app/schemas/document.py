from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    pages: int
    characters: int
    status: str


class DocumentMetadata(DocumentUploadResponse):
    pass


class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


class SourceExcerpt(BaseModel):
    ref: int
    page: int
    text: str
    score: float


class QuestionResponse(BaseModel):
    document_id: str
    question: str
    found: bool
    answer: str
    sources: list[SourceExcerpt]
