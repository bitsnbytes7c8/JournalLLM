from __future__ import annotations

from datetime import date as date_type
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from storage import StorageManager


BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

ui_router = APIRouter(include_in_schema=False)


def get_storage() -> StorageManager:
    return StorageManager()


@ui_router.get("/", response_class=HTMLResponse)
def home(request: Request, sm: StorageManager = Depends(get_storage)):
    latest = sm.get_latest_entries(limit=10)
    entries = [
        {
            "id": str(e["id"]),
            "title": e["title"],
            "journal_date": e["journal_date"].isoformat()
            if isinstance(e["journal_date"], date_type)
            else str(e["journal_date"]),
        }
        for e in latest
    ]
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "entries": entries},
    )


@ui_router.get("/create", response_class=HTMLResponse)
def create(request: Request):
    return templates.TemplateResponse("create.html", {"request": request})


@ui_router.get("/entry/{entry_id}", response_class=HTMLResponse)
def view_entry(request: Request, entry_id: UUID, sm: StorageManager = Depends(get_storage)):
    try:
        entry = sm.get_entry_by_id(entry_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail="Entry not found") from e

    return templates.TemplateResponse(
        "view.html",
        {
            "request": request,
            "entry": {
                "id": str(entry.id),
                "title": entry.title,
                "content": entry.content,
                "mood": entry.mood,
                "journal_date": entry.journal_date.isoformat(),
                "vector_status": entry.vector_status,
            },
        },
    )

