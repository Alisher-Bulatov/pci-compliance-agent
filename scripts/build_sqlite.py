import sqlite3
import re
from pathlib import Path

# Paths
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CHUNKS_FILE = DATA_DIR / "pci_chunks.txt"
DB_FILE = DATA_DIR / "pci_requirements.db"

# Ensure output directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

# SQLite schema
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS requirements (
    id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    tags TEXT DEFAULT ''
);
"""

INSERT_SQL = """
INSERT OR REPLACE INTO requirements (id, text, tags) VALUES (?, ?, ?)
"""


def parse_line(line):
    """Extract ID and text from a formatted requirement line."""
    match = re.match(r"Requirement\s+([0-9.]+):\s+(.*)", line)
    if match:
        return match.group(1), match.group(2)
    return None, None


def build_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(CREATE_TABLE_SQL)

    with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            req_id, text = parse_line(line.strip())
            if req_id and text:
                cursor.execute(INSERT_SQL, (req_id, text, ""))

    conn.commit()
    conn.close()
    print(f"✅ Built database at {DB_FILE}")


if __name__ == "__main__":
    build_db()
