#!/usr/bin/env python3
"""
verify_index_vs_db.py — sanity-check FAISS index & mapping vs SQLite requirements.
"""

import sqlite3, faiss
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DB_FILE = DATA / "pci_requirements.db"
INDEX_FILE = DATA / "pci_index.faiss"

def main():
    if not DB_FILE.exists():
        print(f"❌ Missing DB: {DB_FILE}")
        return
    if not INDEX_FILE.exists():
        print(f"❌ Missing index: {INDEX_FILE}")
        return

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM requirements")
    n_reqs = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*), MIN(faiss_id), MAX(faiss_id) FROM faiss_map")
    row = cur.fetchone()
    map_count = row[0] if row else 0

    index = faiss.read_index(str(INDEX_FILE))
    ntotal = index.ntotal

    print(f"requirements: {n_reqs}  faiss_map: {map_count}  index.ntotal: {ntotal}")
    if n_reqs != map_count or map_count != ntotal:
        print("⚠ Counts differ. Rebuild index (scripts/build_index.py).")
    else:
        print("✅ Counts consistent.")

    # spot check some IDs exist in both
    cur.execute("SELECT faiss_id, rid FROM faiss_map ORDER BY faiss_id LIMIT 10")
    print("sample mapping:", cur.fetchall())

    conn.close()

if __name__ == "__main__":
    main()
