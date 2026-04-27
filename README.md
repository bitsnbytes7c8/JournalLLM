## Local Journal backend (FastAPI + SQLModel)

### What this sets up

- **Storage root**: `~/.local_journal/`
- **Attachments**: `~/.local_journal/attachments/`
- **Vector store**: `~/.local_journal/vector_store/`
- **SQLite DB**: `~/.local_journal/journal.db`

### Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

