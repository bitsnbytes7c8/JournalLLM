## Local Journal backend (FastAPI + SQLModel)

Local-first journal API: SQLite under your home directory, optional image attachments, CORS for a separate frontend, optional **Ollama**-backed enrichment (mood + embeddings), and a **RAG chat** (`InsightsEngine`) over your indexed entries.

### What this sets up

On startup the app ensures:

- **Storage root**: `~/.local_journal/`
- **Attachments**: `~/.local_journal/attachments/`
- **Vector store**: `~/.local_journal/vector_store/` ([ChromaDB](https://www.trychroma.com/) persistent DB + **`journal_entries`** collection; created on demand)
- **SQLite DB**: `~/.local_journal/journal.db`

### Requirements

- Python 3.9+
- Dependencies: see `requirements.txt` (FastAPI, SQLModel, Uvicorn, **jinja2**, **ollama**, **chromadb**)
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
- **Home UI**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

Alternative:

```bash
uvicorn server.app:app --reload
```

### API overview

| Method | Path | Description |
|--------|------|-------------|
| `PUT` | `/entry/{entryId}` | Create or update an entry; see below |
| `POST` | `/entry` | Create a new entry (used by the UI create form) |
| `GET` | `/entry/date/{YYYY-MM-DD}` | List entries for that journal date (summaries) |
| `GET` | `/entry/id/{entryId}` | Full entry plus attachments |
| `GET` | `/entries/latest?limit=N` | Latest entries (id/title/journal_date), ordered by date desc |
| `POST` | `/chat/{session_id}` | RAG chat: session history + Chroma retrieval + Llama 3.2 answer |

**PUT `/entry/{entryId}`**

- **Create** when `entryId` is `new` or the null UUID `00000000-0000-0000-0000-000000000000`.
- **Update** otherwise (UUID string). Returns `{"entryId": "<uuid>"}`.
- After a successful create or update, a **background task** runs (`process_entry_metadata` → shared **`intelligence.entry_pipeline.enrich_and_index_entry`**): reloads the entry, re-describes images via **moondream**, infers **mood** via **llama3.2**, embeds with **nomic-embed-text**, **upserts** into Chroma (`VectorManager` → **`journal_entries`**, ID = entry UUID, metadata **`journal_date`** + **`tags`**), and sets **`vector_status`** to **`ready`** or **`failed`** in SQLite.

Body (`EntryCreate`):

- `title`, `content` (required)
- `attachment` (optional): `{ "localPath": "...", "webUrlPath": "..." }` — local files are copied into `attachments/` and stored as relative paths; URLs are stored for cloud images.

**POST `/entry`**

- Creates a new entry and returns `{"id": "<uuid>"}` (HTTP 201). This is used by the Jinja2 UI `/create` page.

**GET `/entry/date/{date}`**

- Returns a list of `EntrySummary`: `entryId`, `title`.

**GET `/entry/id/{entryId}`**

- Returns `EntryDetail`: `entryId`, `title`, `content`, `journal_date`, and `attachments`.
- For **local** images, each attachment `path` is an **absolute** filesystem path resolved from `~/.local_journal/`. **Cloud** attachments use the stored URL as `path`.

**POST `/chat/{session_id}`**

- **Body:** `{ "message": "<user text>" }` — `ChatRequest`.
- **Response:** `{ "reply": "<assistant text>" }` — `ChatResponse`.
- Uses an in-memory **`InMemorySessionManager`**: before answering, only **prior** turns are in history; the new user message and the assistant reply are appended after `InsightsEngine` returns.
- **`InsightsEngine`** (Llama 3.2 + **nomic-embed-text** + Chroma):
  1. **Intent JSON:** `get_search_intent` → `{"standalone_query", "filters": null}`.
  2. **Retrieval:** embed `standalone_query`, `VectorManager.query_semantic` with a **0.5 max distance** cutoff, load **title + content** from SQLite for the hit IDs.
  3. **Answer:** one Llama 3.2 call with `SYSTEM PROMPT` / `HISTORY` / `CONTEXT` / `QUESTION` sections.

### Maintenance: full re-index

From the repo root (same Ollama/Chroma setup as the server):

```bash
python3 scripts/rebuild_index.py          # prompts before wiping Chroma
python3 scripts/rebuild_index.py --force  # no prompt; deletes collection then rebuilds
```

This **deletes** the Chroma **`journal_entries`** collection, then walks **all SQLite entries** in creation order. For each entry it fills **missing** image descriptions and **missing** mood when possible, always recomputes the embedding and upserts Chroma, and sets **`vector_status`** to **`indexed`** (or **`failed`** on error). Progress is printed (`Processing entry i of n...`).

### Project layout

- `main.py` — minimal entrypoint (`uvicorn.run("server.app:app", ...)`)
- `server/app.py` — FastAPI app, routes, CORS, background tasks, `POST /chat`
- `server/schemas.py` — Pydantic request/response models
- `storage/storage_manager.py` — `StorageManager` (SQLite, files, metadata)
- `storage/session_manager.py` — `InMemorySessionManager` (chat history per `session_id`)
- `storage/vector_manager.py` — `VectorManager` (ChromaDB persistent client, semantic upsert/query, optional `max_distance`)
- `storage/models.py` — SQLModel tables
- `intelligence/interfaces.py` — ABCs for text / image / embedding clients
- `intelligence/ollama_impl.py` — Ollama implementations (`llama3.2`, `moondream`, `nomic-embed-text`)
- `intelligence/insights_engine.py` — RAG: intent JSON, vector search, grounded answer
- `intelligence/entry_pipeline.py` — shared **`enrich_and_index_entry`** (API background job + rebuild script)
- `intelligence/tasks.py` — `process_entry_metadata` (wraps the pipeline for FastAPI `BackgroundTasks`)
- `scripts/rebuild_index.py` — wipe Chroma collection and batch re-index from SQLite
- `ui/router.py` — Jinja2 UI routes (`/`, `/create`, `/entry/{id}`)
- `ui/templates/` — Jinja2 templates (`base.html`, `index.html`, `view.html`, `create.html`)
- `ui/static/` — static assets (mounted at `/static`)
