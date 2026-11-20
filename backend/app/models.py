"""Modèles Pydantic de l'API (contrat décrit dans l'énoncé, section 5)."""
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class Filters(BaseModel):
    type: str | None = Field(default=None, description="Type de document (ex. « FAQ (questions-réponses) »)")
    reference: str | None = Field(default=None, description="Référence d'un document")

    def as_dict(self) -> dict:
        return {k: v for k, v in self.model_dump().items() if v}


class _QuestionMixin(BaseModel):
    question: str = Field(..., description="Question de l'étudiant")
    top_k: int = Field(default=5, ge=1, le=50, description="Nombre de fragments")
    filters: Filters | None = None

    @field_validator("question")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("La question ne peut pas être vide.")
        return v

    def filter_dict(self) -> dict:
        return self.filters.as_dict() if self.filters else {}


class SearchRequest(_QuestionMixin):
    pass


class AskRequest(_QuestionMixin):
    pass


class SearchHit(BaseModel):
    id: int = Field(description="Rang du fragment (1 = le plus proche)")
    chunk_id: str
    file: str
    reference: str
    type: str
    date: str | None
    page: int
    section: str
    text: str
    score: float


class SearchResponse(BaseModel):
    question: str
    results: list[SearchHit]


class Source(BaseModel):
    id: int = Field(description="Numéro de citation : [1], [2]...")
    chunk_id: str
    file: str
    reference: str
    date: str | None
    page: int
    section: str
    excerpt: str
    score: float


class AskResponse(BaseModel):
    answer: str
    found: bool
    sources: list[Source]
    invalid_citations: list[int]
    latency_ms: int


class IngestRequest(BaseModel):
    strategy: Literal["fixed", "structural"] = "structural"
    chunk_size: int | None = Field(default=None, ge=50, le=5000,
                                   description="Taille en caractères (défaut : 500 fixe / 1000 structurel)")
    chunk_overlap: int | None = Field(default=None, ge=0, le=2000)
    contextual_header: bool = True

    @model_validator(mode="after")
    def overlap_below_size(self):
        if self.chunk_size and self.chunk_overlap is not None and self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap doit être strictement inférieur à chunk_size.")
        return self


class IngestDocument(BaseModel):
    file: str
    reference: str
    chunks: int


class IngestResponse(BaseModel):
    documents: int
    chunks: int
    strategy: str
    chunk_size: int
    chunk_overlap: int
    removed_documents: int
    duration_ms: int
    per_document: list[IngestDocument]


class DocumentInfo(BaseModel):
    file: str
    reference: str
    title: str
    type: str
    date: str | None
    version: str
    status: str
    pages: int
    chunks: int
    modifies: list[str]
    modified_by: list[str]


class HealthResponse(BaseModel):
    status: str
    chunks: int
    embedding_model: str
    llm_provider: str
    similarity_threshold: float
