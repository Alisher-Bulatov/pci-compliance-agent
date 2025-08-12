"""Retrieve PCI DSS requirement text for one or more IDs. Accepts id: str or ids: List[str]."""

from __future__ import annotations

from pathlib import Path
import os
import sqlite3
from typing import List, Optional, Literal, Dict, Any

from pydantic import BaseModel, Field

from agent.models.base import BaseToolOutputSchema
from agent.models.requirement import RequirementEntry


# ---- Input / Output Schemas -------------------------------------------------

class InputSchema(BaseModel):
    """
    Backwards-compatible input:
      - Use `id` for a single ID (old behavior).
      - Or `ids` for multiple IDs (new, batched).
    """
    id: Optional[str] = Field(default=None)
    ids: Optional[List[str]] = Field(default=None, description="Max ~20 to avoid giant queries.")


class OutputSchema(BaseToolOutputSchema):
    status: Literal["success", "partial_success", "not_found"]
    tool_name: Literal["get"]
    # result: RequirementEntry | List[RequirementEntry] | None  (declared in BaseToolOutputSchema)


# ---- Constants / DB Path ----------------------------------------------------

# Prefer env overrides; fall back to repo-relative data/
DB_FILE = Path(
    os.getenv("DB_LOCAL_PATH")
    or os.getenv("SQLITE_DB_PATH")
    or (Path(__file__).resolve().parents[1] / "data" / "pci_requirements.db")
)
TABLE = "requirements"


# ---- Helpers ----------------------------------------------------------------

def _open_db() -> sqlite3.Connection:
    if not DB_FILE.exists():
        raise FileNotFoundError(f"SQLite DB not found: {DB_FILE}")
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_entry(row: sqlite3.Row) -> RequirementEntry:
    # expected columns: id TEXT, text TEXT, tags TEXT (CSV or NULL)
    rid = row["id"]
    text = row["text"]
    tags_csv = row["tags"] if "tags" in row.keys() else None
    tags = [t for t in (tags_csv or "").split(",") if t]
    return RequirementEntry(id=rid, text=text, tags=tags)


def _fetch_many(ids: List[str]) -> Dict[str, RequirementEntry]:
    if not ids:
        return {}

    placeholders = ",".join("?" for _ in ids)
    sql = f"SELECT id, text, COALESCE(tags,'') AS tags FROM {TABLE} WHERE id IN ({placeholders})"

    with _open_db() as conn:
        rows = conn.execute(sql, ids).fetchall()

    by_id: Dict[str, RequirementEntry] = {}
    for row in rows:
        entry = _row_to_entry(row)
        by_id[entry.id] = entry
    return by_id


def _normalize_ids(single_id: Optional[str], id_list: Optional[List[str]]) -> List[str]:
    # Merge inputs, strip whitespace, drop empties, de-dup preserve order
    merged: List[str] = []
    if id_list:
        merged.extend(id_list)
    if single_id:
        merged.append(single_id)

    seen = set()
    clean: List[str] = []
    for rid in merged:
        rid = (rid or "").strip()
        if rid and rid not in seen:
            clean.append(rid)
            seen.add(rid)
    return clean


def main(input_data: InputSchema) -> OutputSchema:
    """
    Retrieves one or more requirements by ID.
    - When a single ID is provided (id), returns a single RequirementEntry in `result`.
    - When multiple IDs are provided (ids), returns a list in the same order as requested.
    Status:
      - "success"          → all requested IDs found
      - "partial_success"  → some found, some missing
      - "not_found"        → none found
    """
    clean_ids = _normalize_ids(input_data.id, input_data.ids)

    if not clean_ids:
        return OutputSchema(status="not_found", tool_name="get", result=None, meta={"requested": []})

    MAX_BATCH = 20
    if len(clean_ids) > MAX_BATCH:
        raise ValueError(f"Too many IDs requested ({len(clean_ids)}). Max allowed is {MAX_BATCH}.")

    by_id = _fetch_many(clean_ids)

    # Single-ID path (preserve old behavior)
    if len(clean_ids) == 1:
        rid = clean_ids[0]
        entry = by_id.get(rid)
        if entry is None:
            return OutputSchema(
                status="not_found", tool_name="get", result=None,
                meta={"requested": clean_ids, "db_path": str(DB_FILE)}
            )
        return OutputSchema(status="success", tool_name="get", result=entry, meta={"db_path": str(DB_FILE)})

    # Multi-ID path
    results: List[RequirementEntry] = [by_id[rid] for rid in clean_ids if rid in by_id]
    missing: List[str] = [rid for rid in clean_ids if rid not in by_id]

    if results and not missing:
        return OutputSchema(
            status="success", tool_name="get", result=results,
            meta={"requested": clean_ids, "db_path": str(DB_FILE)}
        )

    if results and missing:
        return OutputSchema(
            status="partial_success", tool_name="get", result=results,
            meta={"requested": clean_ids, "not_found": missing, "db_path": str(DB_FILE)}
        )

    # None found
    return OutputSchema(
        status="not_found", tool_name="get", result=None,
        meta={"requested": clean_ids, "not_found": missing, "db_path": str(DB_FILE)}
    )


# ---- Tool entry for dispatcher ----------------------------------------------

async def run(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Dispatcher entry point (async).
    Accepts a plain dict `params`, builds InputSchema, runs `main`, and returns a plain dict.
    """
    # Accept both {"id": "..."} and {"ids": [...]} (and tolerate "q" alias)
    pid = params.get("id") or params.get("q")
    pids = params.get("ids")

    try:
        input_model = InputSchema(id=pid, ids=pids)
        out = main(input_model)
        return out.model_dump()
    except FileNotFoundError as e:
        return OutputSchema(
            status="not_found", tool_name="get", result=None,
            meta={"error": str(e), "db_path": str(DB_FILE)}
        ).model_dump()
    except Exception as e:
        # Keep errors in meta so the tool response shape stays consistent
        return OutputSchema(
            status="not_found", tool_name="get", result=None,
            meta={"error": f"{e.__class__.__name__}: {e}", "db_path": str(DB_FILE)}
        ).model_dump()
