
# build_index.py — Rebuild FAISS index **from SQLite** (SQLite = source of truth)
import sqlite3
import pickle
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
MAPPING_FILE = DATA_DIR / "mapping.pkl"
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# Snippet length for mapping previews (kept short to discourage using mapping as full SoT)
SNIPPET_CHARS = int(os.getenv("SNIPPET_CHARS", "220"))

def _snippet(text: str, limit: int = SNIPPET_CHARS) -> str:
    t = (text or "").strip().replace("\n", " ")
    if len(t) <= limit:
        return t
    return t[:limit].rsplit(" ", 1)[0] + " …"

def load_rows():
    if not DB_FILE.exists():
        raise FileNotFoundError(f"SQLite DB not found: {DB_FILE}")
    conn = sqlite3.connect(str(DB_FILE))
    cur = conn.cursor()
    cur.execute("SELECT id, text, tags FROM requirements ORDER BY id")
    rows = cur.fetchall()
    conn.close()
    if not rows:
        raise ValueError("No rows found in SQLite 'requirements' table.")
    # Ensure uniqueness & canonical form (strip trailing dots/spaces)
    seen = set()
    out = []
    for rid, text, tags in rows:
        rid_norm = rid.strip().rstrip(".")
        if rid_norm in seen:
            continue
        seen.add(rid_norm)
        out.append((rid_norm, text, tags or ""))
    return out

def main():
    rows = load_rows()

    # Prepare training strings and mapping
    texts = [f"{rid}: {text}" for rid, text, _ in rows]

    # Build mapping with preview snippet; keep full text for convenience but sourced from SQLite
    # (If you prefer NO full text in mapping, set INCLUDE_FULL_TEXT=0 in env.)
    include_full = os.getenv("INCLUDE_FULL_TEXT", "1").lower() not in {"0","false","no"}

    mapping = {}
    for i, (rid, text, tags_csv) in enumerate(rows):
        tags = [t for t in (tags_csv or "").split(",") if t]
        entry = {
            "id": rid,
            "snippet": _snippet(text),
            "tags": tags,
        }
        if include_full:
            entry["text"] = text
        mapping[i] = entry

    # Embed & index
    embedder = SentenceTransformer(EMBEDDING_MODEL)
    embeddings = np.asarray(embedder.encode(texts, show_progress_bar=True), dtype="float32")
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    # Save
    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(INDEX_FILE))
    with open(MAPPING_FILE, "wb") as f:
        pickle.dump(mapping, f)

    print(f"✅ Rebuilt FAISS from SQLite: {len(mapping)} entries -> {INDEX_FILE.name}, {MAPPING_FILE.name}")
    print(f"   Model={EMBEDDING_MODEL}  IncludeFullText={include_full}  SnippetChars={SNIPPET_CHARS}")

if __name__ == "__main__":
    main()

