from __future__ import annotations

import sys
from pathlib import Path

import uvicorn


def main() -> None:
    # Ensure `server` and `storage` packages are importable even when executed
    # from a different working directory.
    project_root = Path(__file__).resolve().parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    uvicorn.run("server.app:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()

