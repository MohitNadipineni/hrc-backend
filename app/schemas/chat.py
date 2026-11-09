from typing import Literal
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    thread_id: UUID | None = None


class Citation(BaseModel):
    tag: str
    source: str
    detail: str


class ChatResponse(BaseModel):
    thread_id: UUID
    message_id: int
    answer: str
    route: str
    citations: list[Citation]
    sql: str | None = None
    warnings: list[str] = []
    standalone_question: str


class ThreadSummary(BaseModel):
    thread_id: UUID
    title: str
    created_at: datetime


class MessageOut(BaseModel):
    message_id: int
    role: str
    content: str
    details: dict
    created_at: datetime


class ThreadDetail(BaseModel):
    thread_id: UUID
    title: str
    created_at: datetime
    messages: list[MessageOut]

class FeedbackRequest(BaseModel):
    message_id: int
    rating: Literal[1, -1]
    comment: str | None = Field(default=None, max_length=1000)