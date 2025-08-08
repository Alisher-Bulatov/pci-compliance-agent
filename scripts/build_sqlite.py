import json
import sqlite3
import re
from pathlib import Path

# Paths
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
JSON_FILE = DATA_DIR / "pciRequirements.json"
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

# Accept keys like "Requirement 1", "Section 1.1", "Section 11.5.1.1", etc.
JSON_KEY_RE = re.compile(r"^(Requirement|Section)\s+(\d[\d.]*)\s*$")

# === Tagging rules (keep in sync with build_index.py) ===
TAG_KEYWORDS = {
    "encryption": [
        "encrypt",
        "cryptographic",
        "cipher",
        "key management",
        "decryption",
        "protect cardholder data",
    ],
    "authentication": [
        "authentication",
        "auth",
        "login",
        "password",
        "PIN",
        "biometric",
    ],
    "network": ["firewall", "router", "network", "packet", "traffic"],
    "compliance": ["compliance", "audit", "responsibility"],
    "storage": ["store", "storage", "retain", "save", "database"],
}

def extract_tags(text: str) -> list[str]:
    tag_set = set()
    lowered = text.lower()
    for tag, keywords in TAG_KEYWORDS.items():
        if any(kw in lowered for kw in keywords):
            tag_set.add(tag)
    return sorted(tag_set)

def build_db():
    if not JSON_FILE.exists():
        raise FileNotFoundError(f"JSON file not found: {JSON_FILE}")

    # Load JSON
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)
        if not isinstance(raw, dict):
            raise ValueError("pciRequirements.json must be a JSON object of key/value pairs.")

    # Parse records
    records: list[tuple[str, str]] = []
    for key, val in raw.items():
        if not isinstance(val, str):
            continue
        m = JSON_KEY_RE.match(key.strip())
        if not m:
            # ignore unknown keys
            continue
        req_id = m.group(2).strip()
        text = val.strip()
        if req_id and text:
            records.append((req_id, text))

    if not records:
        raise ValueError("No valid (id, text) records parsed from pciRequirements.json.")

    # Write DB
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(CREATE_TABLE_SQL)

    inserted = 0
    for req_id, text in records:
        tags = ",".join(extract_tags(text))
        cursor.execute(INSERT_SQL, (req_id, text, tags))
        inserted += 1

    conn.commit()
    conn.close()
    print(f"✅ Built database at {DB_FILE} with {inserted} rows from JSON (tags populated).")

if __name__ == "__main__":
    build_db()
