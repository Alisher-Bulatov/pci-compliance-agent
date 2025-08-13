#!/usr/bin/env python3
"""
build_sqlite.py — Build/refresh SQLite DB from data/pciRequirements.json.

- Accepts "Requirement N", "Section N.N", "Subsection N.N.N" keys.
- Stores:
    id           TEXT PRIMARY KEY  (e.g., "10", "10.6", "10.6.1")
    text         TEXT NOT NULL     (title/description)
    level        TEXT NOT NULL     ("Requirement" | "Section" | "Subsection")
    parent_id    TEXT NULL         (NULL for top-level)
    tags         TEXT NULL         (comma-separated tags; trivial extractor here)

Usage:
  python scripts/build_sqlite.py
"""

import json, re, sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
JSON_FILE = DATA_DIR / "pciRequirements.json"
DB_FILE = DATA_DIR / "pci_requirements.db"

REQ_RE = re.compile(r"^Requirement\s+(\d+)\s*$", re.I)
SEC_RE = re.compile(r"^Section\s+(\d+\.\d+)\s*$", re.I)
SUB_RE = re.compile(r"^Subsection\s+(\d+\.\d+\.\d+)\s*$", re.I)

def level_and_id(key: str):
    key = key.strip()
    m = REQ_RE.match(key)
    if m: return "Requirement", m.group(1)
    m = SEC_RE.match(key)
    if m: return "Section", m.group(1)
    m = SUB_RE.match(key)
    if m: return "Subsection", m.group(1)
    return None, None

def parent_of(code: str):
    parts = code.split(".")
    if len(parts) == 1: return None
    if len(parts) == 2: return parts[0]
    return ".".join(parts[:2])

def extract_tags(text: str) -> list[str]:
    t = text.lower()
    tags = []
    if any(w in t for w in ["log", "audit"]):
        tags.append("logging")
    if "mfa" in t or "multi-factor" in t:
        tags.append("mfa")
    if "vulnerability" in t or "scan" in t:
        tags.append("vuln")
    if "penetration" in t:
        tags.append("pentest")
    if "crypt" in t:
        tags.append("crypto")
    if "firewall" in t or "router" in t or "network" in t:
        tags.append("network")
    return tags

def natural_sort_key(code: str):
    return [int(x) if x.isdigit() else x for x in code.split(".")]

def ensure_schema(conn: sqlite3.Connection):
    # Auto-migrate if the table already exists without new columns
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='requirements'")
    exists = cur.fetchone() is not None
    if exists:
        cur.execute("PRAGMA table_info(requirements)")
        cols = {r[1] for r in cur.fetchall()}
        for missing in ["level", "parent_id", "tags"]:
            if missing not in cols:
                cur.execute(f"ALTER TABLE requirements ADD COLUMN {missing} TEXT")
        conn.commit()
        return

    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS requirements(
        id TEXT PRIMARY KEY,
        text TEXT NOT NULL,
        level TEXT NOT NULL,
        parent_id TEXT,
        tags TEXT
    )""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_parent ON requirements(parent_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_level ON requirements(level)")
    conn.commit()

def main():
    if not JSON_FILE.exists():
        raise SystemExit(f"Missing JSON: {JSON_FILE}")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    data = json.load(open(JSON_FILE, "r", encoding="utf-8"))
    rows = []
    for k, v in data.items():
        lvl, rid = level_and_id(k)
        if not lvl:
            # ignore non-Requirement/Section/Subsection keys
            continue
        text = (v or "").strip()
        rows.append((rid, text, lvl, parent_of(rid), ",".join(extract_tags(text))))

    rows.sort(key=lambda r: natural_sort_key(r[0]))

    conn = sqlite3.connect(DB_FILE)
    ensure_schema(conn)
    cur = conn.cursor()
    cur.execute("DELETE FROM requirements")
    cur.executemany(
        "INSERT OR REPLACE INTO requirements(id, text, level, parent_id, tags) VALUES (?,?,?,?,?)",
        rows
    )
    conn.commit()
    conn.close()
    print(f"✅ Built SQLite at {DB_FILE} with {len(rows)} rows")

if __name__ == "__main__":
    main()
