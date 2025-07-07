from typing import List
from pydantic import BaseModel
from tools.util import get_sqlite_db

class SectionInput(BaseModel):
    section_prefix: str  # e.g., "3.2"

def run_tool(tool_input: SectionInput) -> List[dict]:
    db = get_sqlite_db()
    cursor = db.cursor()
    query = """
        SELECT id, text FROM pci_requirements
        WHERE id LIKE ? ORDER BY id ASC
    """
    like_pattern = f"{tool_input.section_prefix}.%"
    cursor.execute(query, (like_pattern,))
    rows = cursor.fetchall()
    return [{"id": row["id"], "text": row["text"]} for row in rows]
