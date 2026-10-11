from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    session_id: str | None = None


class FeedbackRequest(BaseModel):
    message_id: str
    rating: int = Field(ge=-1, le=1)
    comment: str | None = None


class Citation(BaseModel):
    index: int
    doc_title: str
    page: int | None = None
    section: str = ""
    source: str = ""
    chunk_id: str = ""
    snippet: str = ""
    score: float = 0.0


class TraceStep(BaseModel):
    step: str
    detail: str
    ts: float = 0.0
