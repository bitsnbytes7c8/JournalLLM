## Local Journal backend (FastAPI + SQLModel)

Local-first journal API: SQLite under your home directory, optional image attachments, and CORS enabled for a separate frontend.

### What this sets up

On startup the app ensures:

- **Storage root**: `~/.local_journal/`
- **Attachments**: `~/.local_journal/attachments/`
- **Vector store**: `~/.local_journal/vector_store/`
- **SQLite DB**: `~/.local_journal/journal.db`

### Requirements

- Python 3.9+
- Dependencies: see `requirements.txt` (FastAPI, SQLModel, Uvicorn)

### Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

- **Interactive API docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### API overview

| Method | Path | Description |
|--------|------|-------------|
| `PUT` | `/entry/{entryId}` | Create or update an entry; see below |
| `GET` | `/entry/date/{YYYY-MM-DD}` | List entries for that journal date (summaries) |
| `GET` | `/entry/id/{entryId}` | Full entry plus attachments |

**PUT `/entry/{entryId}`**

- **Create** when `entryId` is `new` or the null UUID `00000000-0000-0000-0000-000000000000`.
- **Update** otherwise (UUID string). Returns `{"entryId": "<uuid>"}`.

Body (`EntryCreate`):

- `title`, `content` (required)
- `attachment` (optional): `{ "localPath": "...", "webUrlPath": "..." }` — local files are copied into `attachments/` and stored as relative paths; URLs are stored for cloud images.

**GET `/entry/date/{date}`**

- Returns a list of `EntrySummary`: `entryId`, `title`.

**GET `/entry/id/{entryId}`**

- Returns `EntryDetail`: `entryId`, `title`, `content`, `journal_date`, and `attachments`.
- For **local** images, each attachment `path` is an **absolute** filesystem path resolved from `~/.local_journal/`. **Cloud** attachments use the stored URL as `path`.

### Project layout

- `app/main.py` — FastAPI app, routes, CORS, `StorageManager` dependency
- `app/storage.py` — `StorageManager` (SQLite, files, path resolution)
- `app/models.py` — SQLModel tables
- `app/schemas.py` — Pydantic request/response models
