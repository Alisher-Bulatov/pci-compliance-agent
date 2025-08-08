"""Retrieve the official wording of a specific PCI DSS requirement by ID."""

from pathlib import Path
import sqlite3
from typing import Literal, Optional

from pydantic import BaseModel

from agent.models.base import BaseToolOutputSchema


class InputSchema(BaseModel):
    requirement_id: str


class RequirementText(BaseModel):
    id: str
    text: str
    tags: list[str]


class OutputSchema(BaseToolOutputSchema):
    tool_name: Literal["get_requirement_text"]
    result: Optional[RequirementText]


# Resolve DB path relative to repo root (../data/pci_requirements.db)
DB_FILE = Path(__file__).resolve().parents[1] / "data" / "pci_requirements.db"


def _row_to_result(row: tuple) -> RequirementText:
    fetched_id, text, tags = row
    tag_list = [t for t in (tags or "").split(",") if t]
    return RequirementText(id=fetched_id, text=text, tags=tag_list)


def main(input_data: InputSchema) -> OutputSchema:
    """
    Fetch a single requirement’s text and tags from the database.

    Status semantics:
      - "success": exact/tolerant match found; result is populated.
      - "not_found": no matching row found; result is None.
      - "error": DB error; 'error' field is populated; result is None.
    """
    req_id_raw = input_data.requirement_id or ""
    req_id = req_id_raw.strip()

    if not DB_FILE.exists():
        return OutputSchema(
            status="error",
            tool_name="get_requirement_text",
            error=f"Database not found at {DB_FILE}",
            result=None,
        )

    try:
        conn = sqlite3.connect(str(DB_FILE))
        cur = conn.cursor()

        # 1) Exact match
        row = cur.execute(
            "SELECT id, text, tags FROM requirements WHERE id = ? LIMIT 1",
            (req_id,),
        ).fetchone()

        # 2) Common formatting variants (trailing dot, stray spaces)
        if not row:
            candidates = []
            if req_id.endswith("."):
                candidates.append(req_id.rstrip("."))
            else:
                candidates.append(req_id + ".")
            if " " in req_id:
                candidates.append(req_id.replace(" ", ""))
            for alt in candidates:
                row = cur.execute(
                    "SELECT id, text, tags FROM requirements WHERE id = ? LIMIT 1",
                    (alt,),
                ).fetchone()
                if row:
                    break

        # 3) Light prefix LIKE if it looks like an ID (e.g., "8.4" -> "8.4%")
        if not row and any(ch.isdigit() for ch in req_id):
            like = req_id.rstrip(".") + "%"
            row = cur.execute(
                "SELECT id, text, tags FROM requirements WHERE id LIKE ? ORDER BY id LIMIT 1",
                (like,),
            ).fetchone()

        conn.close()

    except sqlite3.Error as e:
        try:
            conn.close()
        except Exception:
            pass
        return OutputSchema(
            status="error",
            tool_name="get_requirement_text",
            error=f"SQLite error: {e}",
            result=None,
        )

    if not row:
        # Clear not-found signal instead of pretending text is "Unavailable"
        return OutputSchema(
            status="not_found",
            tool_name="get_requirement_text",
            result=None,
        )

    return OutputSchema(
        status="success",
        tool_name="get_requirement_text",
        result=_row_to_result(row),
    )
