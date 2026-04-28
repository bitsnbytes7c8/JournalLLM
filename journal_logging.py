from __future__ import annotations

import logging
import os


def _env_flag(name: str, default: bool = False) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "y", "on")


def configure_logging() -> None:
    """
    Configure application logging once.

    Enable debug logs by setting:
    - JOURNAL_DEBUG=1
    """
    debug = _env_flag("JOURNAL_DEBUG", default=False)
    level = logging.DEBUG if debug else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

