
# build_sqlite.py — Build/refresh SQLite DB from pciRequirements.json (canonical IDs, tags)
import json
import sqlite3
import re
from pathlib import Path

# Paths
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
JSON_FILE = DATA_DIR / "pciRequirements.json"
DB_FILE = DATA_DIR / "pci_requirements.db"

DATA_DIR.mkdir(parents=True, exist_ok=True)

# Schema (add version/meta later if needed)
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS requirements (
    id   TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    tags TEXT DEFAULT ''
);
"""

INSERT_SQL = "INSERT OR REPLACE INTO requirements (id, text, tags) VALUES (?, ?, ?)"

# Keys like "Requirement 1", "Section 1.1", "Section 11.5.1.1"
JSON_KEY_RE = re.compile(r"^(Requirement|Section)\s+(\d[\d.]*)\s*$")

TAG_KEYWORDS = {
    "encryption": ["encrypt","cryptographic","cipher","key management","decryption","protect cardholder data"],
    "authentication": ["authentication","auth","login","password","PIN","biometric"],
    "network": ["firewall","router","network","packet","traffic"],
    "compliance": ["compliance","audit","responsibility"],
    "storage": ["store","storage","retain","save","database"],
}

def extract_tags(text: str) -> list[str]:
    lowered = (text or "").lower()
    tags = []
    for tag, kws in TAG_KEYWORDS.items():
        if any(kw in lowered for kw in kws):
            tags.append(tag)
    return sorted(set(tags))

def canonical_id(raw: str) -> str:
    return (raw or "").strip().rstrip(".")

def build_db():
    if not JSON_FILE.exists():
        raise FileNotFoundError(f"JSON file not found: {JSON_FILE}")

    with open(JSON_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)
        if not isinstance(raw, dict):
            raise ValueError("pciRequirements.json must be an object of key/value pairs.")

    # Parse and canonicalize
    records = []
    for key, val in raw.items():
        if not isinstance(val, str):
            continue
        m = JSON_KEY_RE.match(key.strip())
        if not m:
            continue
        rid = canonical_id(m.group(2))
        text = val.strip()
        if rid and text:
            records.append((rid, text))

    if not records:
        raise ValueError("No valid (id, text) records parsed from pciRequirements.json.")

    # Deduplicate by canonical ID (keep first occurrence)
    seen = set()
    deduped = []
    for rid, text in records:
        if rid in seen:
            continue
        seen.add(rid)
        deduped.append((rid, text))

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(CREATE_TABLE_SQL)

    inserted = 0
    for rid, text in deduped:
        tags = ",".join(extract_tags(text))
        cur.execute(INSERT_SQL, (rid, text, tags))
        inserted += 1

    conn.commit()
    conn.close()
    print(f"✅ Built SQLite at {DB_FILE} with {inserted} rows (canonical IDs, tags populated).")

if __name__ == "__main__":
    build_db()
