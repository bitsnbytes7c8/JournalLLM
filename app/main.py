from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

from .storage import StorageManager


storage = StorageManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    storage.ensure_storage_ready()
    yield


app = FastAPI(title="Local Journal API", lifespan=lifespan)


class EntryCreate(BaseModel):
    title: str
    content: str
    mood: Optional[str] = None
    journal_date: Optional[date] = None
    local_image_path: Optional[str] = None
    image_description: Optional[str] = None


@app.post("/entries")
def create_entry(payload: EntryCreate):
    return storage.save_entry(**payload.model_dump())


@app.get("/entries/by-date/{yyyy_mm_dd}")
def entries_by_date(yyyy_mm_dd: str):
    y, m, d = (int(x) for x in yyyy_mm_dd.split("-"))
    return storage.get_entries_by_date(date(y, m, d))

