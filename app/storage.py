from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import List, Optional
from uuid import UUID, uuid4

from sqlmodel import Session, SQLModel, create_engine, select

from .models import Entry, Image, ImageType


@dataclass(frozen=True)
class JournalPaths:
    base_dir: Path
    attachments_dir: Path
    vector_store_dir: Path
    db_path: Path


class StorageManager:
    def __init__(self, base_dir: Optional[Path] = None):
        base = base_dir if base_dir is not None else (Path.home() / ".local_journal")
        self.paths = JournalPaths(
            base_dir=base,
            attachments_dir=base / "attachments",
            vector_store_dir=base / "vector_store",
            db_path=base / "journal.db",
        )
        self.engine = create_engine(
            f"sqlite:///{self.paths.db_path}",
            connect_args={"check_same_thread": False},
        )

    def ensure_storage_ready(self) -> None:
        self.paths.base_dir.mkdir(parents=True, exist_ok=True)
        self.paths.attachments_dir.mkdir(parents=True, exist_ok=True)
        self.paths.vector_store_dir.mkdir(parents=True, exist_ok=True)
        SQLModel.metadata.create_all(self.engine)

    def get_absolute_path(self, relative_path: str) -> Path:
        rel = Path(relative_path)
        if rel.is_absolute():
            raise ValueError("relative_path must be relative (e.g. attachments/<uuid>.jpg)")
        return (self.paths.base_dir / rel).resolve()

    def save_entry(
        self,
        *,
        title: str,
        content: str,
        mood: Optional[str] = None,
        journal_date: Optional[date] = None,
        local_image_path: Optional[str] = None,
        image_description: Optional[str] = None,
    ) -> Entry:
        self.ensure_storage_ready()

        jd = journal_date or datetime.now(timezone.utc).date()
        entry = Entry(title=title, content=content, mood=mood, journal_date=jd)

        with Session(self.engine) as session:
            session.add(entry)
            session.commit()
            session.refresh(entry)

            if local_image_path:
                src = Path(local_image_path).expanduser()
                if not src.exists() or not src.is_file():
                    raise FileNotFoundError(f"local_image_path not found: {src}")

                image_id = uuid4()
                dst_name = f"{image_id}{src.suffix}"
                dst_abs = self.paths.attachments_dir / dst_name
                shutil.copy2(src, dst_abs)

                rel_location = str(Path("attachments") / dst_name)
                image = Image(
                    id=image_id,
                    entry_id=entry.id,
                    location=rel_location,
                    image_type=ImageType.local,
                    description=image_description,
                )
                session.add(image)
                session.commit()
                session.refresh(entry)

            return entry

    def update_entry(
        self,
        *,
        entry_id: UUID,
        title: Optional[str] = None,
        content: Optional[str] = None,
        mood: Optional[str] = None,
    ) -> Entry:
        """
        Placeholder update method: updates provided fields and refreshes last_updated_at.
        """
        self.ensure_storage_ready()
        with Session(self.engine) as session:
            entry = session.get(Entry, entry_id)
            if entry is None:
                raise KeyError(f"Entry not found: {entry_id}")

            if title is not None:
                entry.title = title
            if content is not None:
                entry.content = content
            if mood is not None:
                entry.mood = mood

            entry.last_updated_at = datetime.now(timezone.utc)
            session.add(entry)
            session.commit()
            session.refresh(entry)
            return entry

    def get_entries_by_date(self, target_date: date) -> List[Entry]:
        self.ensure_storage_ready()

        with Session(self.engine) as session:
            stmt = (
                select(Entry)
                .where(Entry.journal_date == target_date)
                .order_by(Entry.created_at.desc())
            )
            return list(session.exec(stmt).all())

