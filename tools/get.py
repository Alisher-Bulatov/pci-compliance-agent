"""Retrieve PCI DSS requirement text for one or more IDs. Accepts id: str or ids: List[str]."""

from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import List, Optional, Literal, Dict

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

# Resolve DB relative to repo root (../data/pci_requirements.db)
DB_FILE = Path(__file__).resolve().parents[1] / "data" / "pci_requirements.db"
TABLE = "requirements"


# ---- Helpers ----------------------------------------------------------------

def _row_to_entry(row: sqlite3.Row) -> RequirementEntry:
    rid, text, tags_csv = row
    tags = [t for t in (tags_csv or "").split(",") if t]
    return RequirementEntry(id=rid, text=text, tags=tags)


def _fetch_many(ids: List[str]) -> Dict[str, RequirementEntry]:
    if not ids:
        return {}

    if not DB_FILE.exists():
        raise FileNotFoundError(f"SQLite DB not found: {DB_FILE}")

    placeholders = ",".join("?" for _ in ids)
    sql = f"SELECT id, text, tags FROM {TABLE} WHERE id IN ({placeholders})"

    conn = sqlite3.connect(str(DB_FILE))
    try:
        cur = conn.execute(sql, ids)
        rows = cur.fetchall()
    finally:
        conn.close()

    by_id: Dict[str, RequirementEntry] = {}
    for row in rows:
        entry = _row_to_entry(row)
        by_id[entry.id] = entry
    return by_id


# ---- Main Tool Entry --------------------------------------------------------

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
    # Normalize inputs
    if input_data.ids and input_data.id:
        # If both provided, prioritize the explicit list (clear intent) and include the single if not present
        ids = input_data.ids[:]
        if input_data.id not in ids:
            ids.append(input_data.id)
    elif input_data.ids:
        ids = input_data.ids[:]
    elif input_data.id:
        ids = [input_data.id]
    else:
        raise ValueError("Provide id or ids")

    # Basic hygiene
    # - strip whitespace
    # - drop empties
    # - de-dup while preserving order
    seen = set()
    clean_ids: List[str] = []
    for rid in ids:
        rid = (rid or "").strip()
        if rid and rid not in seen:
            clean_ids.append(rid)
            seen.add(rid)

    if not clean_ids:
        return OutputSchema(status="not_found", tool_name="get", result=None, meta={"requested": ids})

    # Batch cap to avoid giant IN (...) queries
    MAX_BATCH = 20
    if len(clean_ids) > MAX_BATCH:
        raise ValueError(f"Too many IDs requested ({len(clean_ids)}). Max allowed is {MAX_BATCH}.")

    by_id = _fetch_many(clean_ids)

    # Single-ID path (preserve old behavior)
    if len(clean_ids) == 1:
        rid = clean_ids[0]
        entry = by_id.get(rid)
        if entry is None:
            return OutputSchema(status="not_found", tool_name="get", result=None, meta={"requested": clean_ids})
        return OutputSchema(status="success", tool_name="get", result=entry)

    # Multi-ID path
    results: List[RequirementEntry] = [by_id[rid] for rid in clean_ids if rid in by_id]
    missing: List[str] = [rid for rid in clean_ids if rid not in by_id]

    if results and not missing:
        return OutputSchema(status="success", tool_name="get", result=results, meta={"requested": clean_ids})

    if results and missing:
        return OutputSchema(
            status="partial_success",
            tool_name="get",
            result=results,
            meta={"requested": clean_ids, "not_found": missing},
        )

    # None found
    return OutputSchema(
        status="not_found",
        tool_name="get",
        result=None,
        meta={"requested": clean_ids, "not_found": missing},
    )
