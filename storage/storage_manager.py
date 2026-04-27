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
    """
    Local-first storage for the journal.

    Uses:
    - ~/.local_journal/journal.db
    - ~/.local_journal/attachments/
    - ~/.local_journal/vector_store/
    """

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

    def _add_local_attachment(
        self,
        *,
        session: Session,
        entry_id: UUID,
        local_image_path: str,
        image_description: Optional[str] = None,
    ) -> Image:
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
            entry_id=entry_id,
            location=rel_location,
            image_type=ImageType.local,
            description=image_description,
        )
        session.add(image)
        session.commit()
        session.refresh(image)
        return image

    def _add_cloud_attachment(
        self,
        *,
        session: Session,
        entry_id: UUID,
        web_url_path: str,
        image_description: Optional[str] = None,
    ) -> Image:
        image = Image(
            entry_id=entry_id,
            location=web_url_path,
            image_type=ImageType.cloud,
            description=image_description,
        )
        session.add(image)
        session.commit()
        session.refresh(image)
        return image

    def save_entry(
        self,
        *,
        title: str,
        content: str,
        mood: Optional[str] = None,
        journal_date: Optional[date] = None,
        local_image_path: Optional[str] = None,
        web_url_path: Optional[str] = None,
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
                self._add_local_attachment(
                    session=session,
                    entry_id=entry.id,
                    local_image_path=local_image_path,
                    image_description=image_description,
                )
            if web_url_path:
                self._add_cloud_attachment(
                    session=session,
                    entry_id=entry.id,
                    web_url_path=web_url_path,
                    image_description=image_description,
                )

            return entry

    def update_entry(
        self,
        *,
        entry_id: UUID,
        title: Optional[str] = None,
        content: Optional[str] = None,
        mood: Optional[str] = None,
        local_image_path: Optional[str] = None,
        web_url_path: Optional[str] = None,
        image_description: Optional[str] = None,
    ) -> Entry:
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

            if local_image_path:
                self._add_local_attachment(
                    session=session,
                    entry_id=entry.id,
                    local_image_path=local_image_path,
                    image_description=image_description,
                )
            if web_url_path:
                self._add_cloud_attachment(
                    session=session,
                    entry_id=entry.id,
                    web_url_path=web_url_path,
                    image_description=image_description,
                )

            session.refresh(entry)
            return entry

    def get_entry_by_id(self, entry_id: UUID) -> Entry:
        self.ensure_storage_ready()
        with Session(self.engine) as session:
            entry = session.get(Entry, entry_id)
            if entry is None:
                raise KeyError(f"Entry not found: {entry_id}")
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

