## Local Journal backend (FastAPI + SQLModel)

Local-first journal API: SQLite under your home directory, optional image attachments, CORS for a separate frontend, and optional **Ollama**-backed enrichment (mood + embeddings).

### What this sets up

On startup the app ensures:

- **Storage root**: `~/.local_journal/`
- **Attachments**: `~/.local_journal/attachments/`
- **Vector store**: `~/.local_journal/vector_store/` ([ChromaDB](https://www.trychroma.com/) persistent DB + **`journal_entries`** collection; created on demand)
- **SQLite DB**: `~/.local_journal/journal.db`

### Requirements

- Python 3.9+
- Dependencies: see `requirements.txt` (FastAPI, SQLModel, Uvicorn, **ollama**, **chromadb**)
- **Optional — AI enrichment**: [Ollama](https://ollama.com) running locally with these models pulled:

  ```bash
  ollama pull llama3.2
  ollama pull moondream
  ollama pull nomic-embed-text
  ```

  If Ollama is missing or a model errors, background jobs set `vector_status` to `failed` on that entry.

- **Environment**: `OLLAMA_HOST` is optional (e.g. `http://127.0.0.1:11434`) — passed through to the Ollama client when set.

### Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

- **Interactive API docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Alternative:

```bash
uvicorn server.app:app --reload
```

### API overview

| Method | Path | Description |
|--------|------|-------------|
| `PUT` | `/entry/{entryId}` | Create or update an entry; see below |
| `GET` | `/entry/date/{YYYY-MM-DD}` | List entries for that journal date (summaries) |
| `GET` | `/entry/id/{entryId}` | Full entry plus attachments |

**PUT `/entry/{entryId}`**

- **Create** when `entryId` is `new` or the null UUID `00000000-0000-0000-0000-000000000000`.
- **Update** otherwise (UUID string). Returns `{"entryId": "<uuid>"}`.
- After a successful create or update, a **background task** runs (`process_entry_metadata`): loads the entry, optionally describes images via **moondream**, infers a short **mood** via **llama3.2**, embeds the combined text with **nomic-embed-text**, **upserts** into Chroma (`VectorManager` → collection **`journal_entries`**, ID = entry UUID, metadata includes **`journal_date`** and **`tags`** (empty for now)), and updates **`mood`** and **`vector_status`** (`ready` or `failed`) in SQLite.

Body (`EntryCreate`):

- `title`, `content` (required)
- `attachment` (optional): `{ "localPath": "...", "webUrlPath": "..." }` — local files are copied into `attachments/` and stored as relative paths; URLs are stored for cloud images.

**GET `/entry/date/{date}`**

- Returns a list of `EntrySummary`: `entryId`, `title`.

**GET `/entry/id/{entryId}`**

- Returns `EntryDetail`: `entryId`, `title`, `content`, `journal_date`, and `attachments`.
- For **local** images, each attachment `path` is an **absolute** filesystem path resolved from `~/.local_journal/`. **Cloud** attachments use the stored URL as `path`.

### Project layout

- `main.py` — minimal entrypoint (`uvicorn.run("server.app:app", ...)`)
- `server/app.py` — FastAPI app, routes, CORS, background tasks
- `server/schemas.py` — Pydantic request/response models
- `storage/storage_manager.py` — `StorageManager` (SQLite, files, metadata)
- `storage/vector_manager.py` — `VectorManager` (ChromaDB persistent client, semantic upsert/query/delete)
- `storage/models.py` — SQLModel tables
- `intelligence/interfaces.py` — ABCs for text / image / embedding clients
- `intelligence/ollama_impl.py` — Ollama implementations (`llama3.2`, `moondream`, `nomic-embed-text`)
- `intelligence/tasks.py` — `process_entry_metadata` background pipeline
