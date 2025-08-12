import threading
import os
import sqlite3
from functools import lru_cache
from typing import List, Dict, Any

import faiss
import numpy as np

# -----------------------------------------------------------------------------
# Thread locks (guard one-time loads under concurrency)
# -----------------------------------------------------------------------------
_index_lock = threading.Lock()
_embedder_lock = threading.Lock()

# -----------------------------------------------------------------------------
# Env helpers
# -----------------------------------------------------------------------------
def _env(name: str, default: str) -> str:
    return (os.getenv(name, default) or "").strip()

def _index_path() -> str:
    # Prefer the path your startup script downloads to; fall back to legacy var.
    return _env("FAISS_LOCAL_PATH", _env("FAISS_INDEX_PATH", "data/pci_index.faiss"))

def _db_path() -> str:
    # Prefer the path your startup script downloads to; fall back to legacy var.
    return _env("DB_LOCAL_PATH", _env("SQLITE_DB_PATH", "data/pci_requirements.db"))

# -----------------------------------------------------------------------------
# Cached loaders
# -----------------------------------------------------------------------------
@lru_cache(maxsize=1)
def get_index(path: str | None = None):
    """
    Load the FAISS index once (thread-safe, cached).
    """
    p = path or _index_path()
    with _index_lock:
        return faiss.read_index(p)

@lru_cache(maxsize=1)
def get_embedder():
    """
    Lazy-load the SentenceTransformer on first use only.
    This avoids importing `transformers` at process start.
    """
    with _embedder_lock:
        # Lazy import to keep app startup fast
        from sentence_transformers import SentenceTransformer  # heavy import
        model_name = _env("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        return SentenceTransformer(model_name)

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _map_faiss_ids_to_rids(db_path: str, ids: List[int]) -> Dict[int, str]:
    if not ids:
        return {}
    conn = sqlite3.connect(db_path)
    try:
        q = ",".join(["?"] * len(ids))
        rows = conn.execute(
            f"SELECT faiss_id, rid FROM faiss_map WHERE faiss_id IN ({q})",
            ids,
        ).fetchall()
        return {int(fid): rid for (fid, rid) in rows}
    finally:
        conn.close()

# -----------------------------------------------------------------------------
# Retriever
# -----------------------------------------------------------------------------
class PCIDocumentRetriever:
    def __init__(self, index_path: str | None = None, db_path: str | None = None):
        self.index = get_index(index_path)
        self.embedder = get_embedder()
        self.db_path = db_path or _db_path()

    def retrieve(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """
        Return minimal doc refs [{"id": rid}, ...] for downstream enrichment.
        """
        if not query or not isinstance(query, str):
            return []

        # Encode to float32 (FAISS expects float32)
        vec = self.embedder.encode([query], normalize_embeddings=False)  # keep default unless your index is IP+normalized
        qv = np.asarray(vec, dtype="float32")
        if qv.ndim == 1:
            qv = qv.reshape(1, -1)

        D, I = self.index.search(qv, k)
        ids = [int(x) for x in I[0].tolist() if x != -1]
        if not ids:
            return []

        by_id = _map_faiss_ids_to_rids(self.db_path, ids)
        return [{"id": rid} for fid in ids if (rid := by_id.get(fid))]

# -----------------------------------------------------------------------------
# Cache control
# -----------------------------------------------------------------------------
def clear_caches():
    get_index.cache_clear()
    get_embedder.cache_clear()
