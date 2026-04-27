from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel


class ImageType(str, Enum):
    local = "local"
    cloud = "cloud"


class Entry(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    title: str
    content: str
    mood: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    journal_date: date = Field(index=True)
    last_updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    vector_status: str = Field(default="pending", index=True)

    images: List["Image"] = Relationship(
        back_populates="entry",
        sa_relationship_kwargs={"lazy": "selectin", "cascade": "all, delete-orphan"},
    )


class Image(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    entry_id: UUID = Field(foreign_key="entry.id", index=True)
    location: str
    image_type: ImageType = Field(index=True)
    description: Optional[str] = None

    entry: Optional[Entry] = Relationship(back_populates="images")

