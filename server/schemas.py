from __future__ import annotations

from datetime import date
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AttachmentIn(BaseModel):
    localPath: Optional[str] = None
    webUrlPath: Optional[str] = None


class EntryCreate(BaseModel):
    title: str
    content: str
    attachment: Optional[AttachmentIn] = None


class EntrySummary(BaseModel):
    entryId: UUID
    title: str


class AttachmentOut(BaseModel):
    attachmentId: UUID
    path: str
    imageType: str = Field(description="local or cloud")
    description: Optional[str] = None


class EntryDetail(BaseModel):
    entryId: UUID
    title: str
    content: str
    journal_date: date
    attachments: List[AttachmentOut]


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    standalone_query: str
    answer: str

