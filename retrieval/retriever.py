import threading
import os
import sqlite3
from functools import lru_cache
from typing import List, Dict, Any

import faiss
import numpy as np

_index_lock = threading.Lock()
_embedder_lock = threading.Lock()

def _env(name: str, default: str) -> str:
    return (os.getenv(name, default) or "").strip()

def _index_path() -> str:
    return _env("FAISS_LOCAL_PATH", _env("FAISS_INDEX_PATH", "data/pci_index.faiss"))

def _db_path() -> str:
    return _env("DB_LOCAL_PATH", _env("SQLITE_DB_PATH", "data/pci_requirements.db"))

@lru_cache(maxsize=1)
def get_index(path: str | None = None):
    p = path or _index_path()
    with _index_lock:
        return faiss.read_index(p)

@lru_cache(maxsize=1)
def get_embedder():
    """
    Load SentenceTransformer **without** hitting the internet:
      - If EMBEDDING_MODEL_PATH points to a local dir, load from there.
      - Else use EMBEDDING_MODEL (default all-MiniLM-L6-v2), which must be pre-cached in the image.
    Set SENTENCE_TRANSFORMERS_HOME to your baked cache dir in the Docker image.
    """
    with _embedder_lock:
        from sentence_transformers import SentenceTransformer  # heavy import

        local_path = _env("EMBEDDING_MODEL_PATH", "")
        if local_path and os.path.isdir(local_path):
            return SentenceTransformer(local_path)

        model_name = _env("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        return SentenceTransformer(model_name)

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

class PCIDocumentRetriever:
    def __init__(self, index_path: str | None = None, db_path: str | None = None):
        self.index = get_index(index_path)
        self.db_path = db_path or _db_path()
        self._dim = self.index.d  # sanity

    def _embed_query(self, q: str) -> np.ndarray:
        model = get_embedder()
        v = model.encode([q], normalize_embeddings=True)
        return v.astype(np.float32)

    def search(self, query: str, k: int = 8) -> List[Dict[str, Any]]:
        if not query or not query.strip():
            return []
        qv = self._embed_query(query.strip())
        if qv.shape[1] != self._dim:
            # Mismatched index/model ⇒ clear cache and raise
            get_embedder.cache_clear()
            raise RuntimeError(f"Embedding dim {qv.shape[1]} != index dim {self._dim}")

        D, I = self.index.search(qv, k)
        ids = [int(x) for x in I[0].tolist() if x != -1]
        if not ids:
            return []
        by_id = _map_faiss_ids_to_rids(self.db_path, ids)
        return [{"id": rid} for fid in ids if (rid := by_id.get(fid))]

def clear_caches():
    get_index.cache_clear()
    get_embedder.cache_clear()
