from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date
from typing import List
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from server.schemas import EntryCreate, EntryDetail, EntrySummary
from storage import ImageType, StorageManager


storage = StorageManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    storage.ensure_storage_ready()
    yield


app = FastAPI(title="Local Journal API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_storage() -> StorageManager:
    return storage


NULL_UUID = UUID("00000000-0000-0000-0000-000000000000")


@app.put("/entry/{entryId}")
def put_entry(
    entryId: str,
    payload: EntryCreate,
    sm: StorageManager = Depends(get_storage),
):
    is_new = entryId == "new"
    parsed_id: UUID
    if not is_new:
        try:
            parsed_id = UUID(entryId)
        except ValueError as e:
            raise HTTPException(status_code=400, detail="entryId must be 'new' or a UUID") from e
        if parsed_id == NULL_UUID:
            is_new = True

    attachment = payload.attachment
    local_path = attachment.localPath if attachment else None
    web_url_path = attachment.webUrlPath if attachment else None

    if is_new:
        entry = sm.save_entry(
            title=payload.title,
            content=payload.content,
            local_image_path=local_path,
            web_url_path=web_url_path,
        )
        return {"entryId": str(entry.id)}

    try:
        entry = sm.update_entry(
            entry_id=parsed_id,
            title=payload.title,
            content=payload.content,
            local_image_path=local_path,
            web_url_path=web_url_path,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Entry not found")

    return {"entryId": str(entry.id)}


@app.get("/entry/date/{date_str}", response_model=List[EntrySummary])
def get_entries_by_date(
    date_str: str,
    sm: StorageManager = Depends(get_storage),
):
    try:
        target = date.fromisoformat(date_str)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD") from e

    entries = sm.get_entries_by_date(target)
    return [EntrySummary(entryId=e.id, title=e.title) for e in entries]


@app.get("/entry/id/{entryId}", response_model=EntryDetail)
def get_entry_by_id(
    entryId: UUID,
    sm: StorageManager = Depends(get_storage),
):
    try:
        entry = sm.get_entry_by_id(entryId)
    except KeyError:
        raise HTTPException(status_code=404, detail="Entry not found")

    attachments = []
    for img in entry.images:
        if img.image_type == ImageType.local:
            path = str(sm.get_absolute_path(img.location))
        else:
            path = img.location
        attachments.append(
            {
                "attachmentId": img.id,
                "path": path,
                "imageType": img.image_type.value,
                "description": img.description,
            }
        )

    return EntryDetail(
        entryId=entry.id,
        title=entry.title,
        content=entry.content,
        journal_date=entry.journal_date,
        attachments=attachments,
    )

