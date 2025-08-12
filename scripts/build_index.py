# build_index.py — Rebuild FAISS index **from SQLite** (SQLite = source of truth)
import sqlite3
from pathlib import Path
import os
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# === Config ===
ROOT_DIR = Path(__file__).resolve().parent.parent  # go up from /scripts
DATA_DIR = ROOT_DIR / "data"
DB_FILE = DATA_DIR / "pci_requirements.db"
INDEX_FILE = DATA_DIR / "pci_index.faiss"

# Embedding
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
INCLUDE_FULL_TEXT = os.getenv("INDEX_INCLUDE_FULL_TEXT", "0").lower() in {"1", "true", "yes"}
SNIPPET_CHARS = int(os.getenv("INDEX_SNIPPET_CHARS", "280"))

def snippet(text: str, limit: int) -> str:
    t = (text or "").strip().replace("\n", " ")
    if len(t) <= limit:
        return t
    return t[:limit].rsplit(" ", 1)[0] + " …"

def load_rows():
    if not DB_FILE.exists():
        raise FileNotFoundError(f"SQLite DB not found: {DB_FILE}")
    conn = sqlite3.connect(str(DB_FILE))
    cur = conn.cursor()
    # Expect schema: requirements(id TEXT PRIMARY KEY, text TEXT, tags TEXT)
    cur.execute("SELECT id, text, tags FROM requirements ORDER BY id")
    rows = cur.fetchall()
    conn.close()
    if not rows:
        raise ValueError("No rows found in SQLite 'requirements' table.")
    # Canonicalize and dedupe
    seen = set()
    out = []
    for rid, text, tags in rows:
        rid_norm = (rid or "").strip().rstrip(".")
        if not rid_norm or rid_norm in seen:
            continue
        seen.add(rid_norm)
        out.append((rid_norm, text or "", tags or ""))
    return out

def ensure_map_table(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS faiss_map(
            faiss_id INTEGER PRIMARY KEY,
            rid TEXT NOT NULL,
            UNIQUE(faiss_id),
            FOREIGN KEY(rid) REFERENCES requirements(id)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_faiss_map_rid ON faiss_map(rid)")

def main():
    rows = load_rows()

    # Training strings for embedding
    texts = []
    for rid, text, tags in rows:
        if INCLUDE_FULL_TEXT:
            texts.append(text.strip())
        else:
            texts.append(snippet(text, SNIPPET_CHARS))

    # Embed
    embedder = SentenceTransformer(EMBEDDING_MODEL)
    embeddings = np.asarray(embedder.encode(texts, show_progress_bar=True), dtype="float32")
    dim = embeddings.shape[1]

    # Build ID-mapped index with stable labels [0..N-1]
    ids = np.arange(len(texts), dtype="int64")
    base = faiss.IndexFlatL2(dim)
    index = faiss.IndexIDMap(base)
    index.add_with_ids(embeddings, ids)

    # Persist index
    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(INDEX_FILE))

    # Persist mapping (faiss_id → rid) into SQLite
    conn = sqlite3.connect(str(DB_FILE))
    try:
        ensure_map_table(conn)
        conn.execute("DELETE FROM faiss_map")
        conn.executemany("INSERT INTO faiss_map(faiss_id, rid) VALUES(?, ?)", list(zip(ids.tolist(), [r[0] for r in rows])))
        conn.commit()
    finally:
        conn.close()

    print(f"✅ Rebuilt FAISS (IDMap) with {len(rows)} entries -> {INDEX_FILE.name}")
    print(f"   Mapping saved in SQLite table 'faiss_map' (faiss_id→rid)")
    print(f"   Model={EMBEDDING_MODEL}  IncludeFullText={INCLUDE_FULL_TEXT}  SnippetChars={SNIPPET_CHARS}")

if __name__ == "__main__":
    main()
