from __future__ import annotations

import sys
from pathlib import Path

import uvicorn
from fastapi.staticfiles import StaticFiles

from server.app import app as api_app
from ui.router import ui_router

def main() -> None:
    # Ensure `server` and `storage` packages are importable even when executed
    # from a different working directory.
    project_root = Path(__file__).resolve().parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()


# App assembly (UI + API)
app = api_app
app.mount(
    "/static",
    StaticFiles(directory=str(Path(__file__).resolve().parent / "ui" / "static")),
    name="static",
)
app.include_router(ui_router)

