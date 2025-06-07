from pathlib import Path
import sqlite3
from typing import Literal

from pydantic import BaseModel

from agent.tool_schema import BaseToolOutputSchema


class InputSchema(BaseModel):
    requirement_id: str


class RequirementText(BaseModel):
    id: str
    text: str
    tags: list[str]


class OutputSchema(BaseToolOutputSchema):
    tool_name: Literal["get_requirement_text"]
    result: RequirementText


DB_PATH = Path(__file__).resolve().parent.parent / "data" / "pci_requirements.db"


def main(input_data: InputSchema) -> OutputSchema:
    """Fetch a single requirement’s text and tags from the database."""
    req_id = input_data.requirement_id

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, text, tags FROM requirements WHERE id = ?", (req_id,)
            )
            row = cursor.fetchone()
    except sqlite3.Error as e:
        return OutputSchema(
            tool_name="get_requirement_text",
            result=RequirementText(
                id=req_id,
                text=f"❌ Database error: {e}",
                tags=[],
            ),
        )

    if not row:
        return OutputSchema(
            tool_name="get_requirement_text",
            result=RequirementText(id=req_id, text="Unavailable", tags=[]),
        )

    fetched_id, text, tags = row
    tag_list = tags.split(",") if tags else []

    return OutputSchema(
        tool_name="get_requirement_text",
        result=RequirementText(id=fetched_id, text=text, tags=tag_list),
    )
