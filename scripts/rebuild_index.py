#!/usr/bin/env python3
"""Full re-index: wipe Chroma ``journal_entries``, rebuild from SQLite."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Wipe ChromaDB journal_entries and re-index all SQLite entries.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation (destructive: deletes the vector collection first).",
    )
    args = parser.parse_args()

    if not args.force:
        prompt = (
            "This will DELETE the ChromaDB collection 'journal_entries' under "
            "~/.local_journal/vector_store and rebuild from SQLite. Continue? [y/N]: "
        )
        if input(prompt).strip().lower() not in ("y", "yes"):
            print("Aborted.")
            sys.exit(0)

    from intelligence.entry_pipeline import enrich_and_index_entry
    from intelligence.ollama_impl import (
        OllamaEmbeddingClient,
        OllamaImageClient,
        OllamaTextClient,
    )
    from storage import StorageManager, VectorManager

    sm = StorageManager()
    vm = VectorManager()
    text_llm = OllamaTextClient()
    image_llm = OllamaImageClient()
    embed_client = OllamaEmbeddingClient()

    sm.ensure_storage_ready()
    print("Wiping Chroma collection 'journal_entries'...", flush=True)
    vm.wipe_journal_collection()

    entries = sm.list_all_entries()
    total = len(entries)
    if total == 0:
        print("No entries in SQLite. Nothing to index.", flush=True)
        return

    for i, entry in enumerate(entries, start=1):
        print(f"Processing entry {i} of {total}... (id={entry.id})", flush=True)
        enrich_and_index_entry(
            entry.id,
            sm=sm,
            vm=vm,
            text_llm=text_llm,
            image_llm=image_llm,
            embed_client=embed_client,
            only_fill_missing=True,
            vector_status_success="indexed",
        )

    print(f"Finished re-indexing {total} entr{'y' if total == 1 else 'ies'}.", flush=True)


if __name__ == "__main__":
    main()
