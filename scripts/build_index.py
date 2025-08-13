#!/usr/bin/env python3
"""
build_index.py — Build FAISS index from SQLite "requirements" table.

- Uses SentenceTransformer for embeddings.
- Saves index to data/pci_index.faiss.
- Also creates/refreshes "faiss_map(faiss_id INTEGER PRIMARY KEY, rid TEXT NOT NULL)"
  to map FAISS vector IDs to requirement IDs.

Usage:
  python scripts/build_index.py [--model all-MiniLM-L6-v2]
"""

import argparse, os, sqlite3, numpy as np, faiss
from pathlib import Path
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DB_FILE = DATA / "pci_requirements.db"
INDEX_FILE = DATA / "pci_index.faiss"

def read_rows():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT id, text FROM requirements ORDER BY id")
    rows = cur.fetchall()
    conn.close()
    return rows

def ensure_map_table(conn):
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS faiss_map(
        faiss_id INTEGER PRIMARY KEY,
        rid TEXT NOT NULL
    )
    """)
    conn.commit()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="all-MiniLM-L6-v2")
    args = ap.parse_args()

    rows = read_rows()
    if not rows:
        raise SystemExit("No rows found in requirements; run build_sqlite.py first.")

    model = SentenceTransformer(args.model)
    texts = [f"{rid} — {txt}" for rid, txt in rows]
    X = model.encode(texts, convert_to_numpy=True, show_progress_bar=True)
    X = X.astype("float32")

    d = X.shape[1]
    base_index = faiss.IndexFlatIP(d)
    index = faiss.IndexIDMap(base_index)

    ids = np.arange(len(rows), dtype="int64")
    index.add_with_ids(X, ids)
    faiss.write_index(index, str(INDEX_FILE))

    # map table
    conn = sqlite3.connect(DB_FILE)
    try:
        ensure_map_table(conn)
        conn.execute("DELETE FROM faiss_map")
        conn.executemany("INSERT INTO faiss_map(faiss_id, rid) VALUES(?,?)", list(zip(ids.tolist(), [r[0] for r in rows])))
        conn.commit()
    finally:
        conn.close()

    print(f"✅ Saved {INDEX_FILE.name} with {len(rows)} vectors. Mapping written to faiss_map.")

if __name__ == "__main__":
    main()
