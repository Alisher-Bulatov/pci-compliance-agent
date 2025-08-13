# retrieval/hierarchy.py
from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import List, Optional

import os

# Reuse the same env vars/paths you already use for tools/search.py
def _db_path() -> Path:
    override = (os.getenv("DB_LOCAL_PATH") or os.getenv("SQLITE_DB_PATH") or "").strip()
    if override:
        return Path(override)
    # fallback to repo data/
    return Path(__file__).resolve().parents[1] / "data" / "pci_requirements.db"

def expand_requirement_ids(root_id: str, include_root: bool = True) -> List[str]:
    """
    Returns [root_id, root_id.*] ordered by numeric segments.
    Works for any depth (e.g., 2, 2.1, 2.1.3).
    """
    db = sqlite3.connect(str(_db_path()))
    db.row_factory = sqlite3.Row
    try:
        ids: List[str] = []

        if include_root:
            row = db.execute("SELECT id FROM requirements WHERE id = ?", (root_id,)).fetchone()
            if row:
                ids.append(row["id"])

        like_pattern = f"{root_id}.%"
        rows = db.execute(
            "SELECT id FROM requirements WHERE id LIKE ? ORDER BY id",
            (like_pattern,),
        ).fetchall()
        ids.extend([r["id"] for r in rows])
        return ids
    finally:
        db.close()

def looks_like_parent(rid: str) -> bool:
    # Treat anything without a dot OR that is a “Section” with children as a parent
    return "." not in rid
