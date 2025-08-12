import threading
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from functools import lru_cache
import os
import sqlite3
from typing import List, Dict, Any

# Thread locks
_index_lock = threading.Lock()
_embedder_lock = threading.Lock()

def _env(name: str, default: str) -> str:
    return (os.getenv(name, default) or "").strip()

@lru_cache(maxsize=1)
def get_index(path=None):
    p = path or _env("FAISS_INDEX_PATH", "data/pci_index.faiss")
    with _index_lock:
        return faiss.read_index(p)

@lru_cache(maxsize=1)
def get_embedder():
    with _embedder_lock:
        return SentenceTransformer(_env("EMBEDDING_MODEL", "all-MiniLM-L6-v2"))

def _map_faiss_ids_to_rids(db_path: str, ids: List[int]) -> Dict[int, str]:
    if not ids:
        return {}
    conn = sqlite3.connect(db_path)
    try:
        q = ",".join(["?"] * len(ids))
        rows = conn.execute(f"SELECT faiss_id, rid FROM faiss_map WHERE faiss_id IN ({q})", ids).fetchall()
        return {int(fid): rid for (fid, rid) in rows}
    finally:
        conn.close()

class PCIDocumentRetriever:
    def __init__(self, index_path=None, db_path=None):
        self.index = get_index(index_path)
        self.embedder = get_embedder()
        self.db_path = db_path or _env("SQLITE_DB_PATH", "data/pci_requirements.db")

    def retrieve(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        if not query or not isinstance(query, str):
            return []
        qv = np.asarray(self.embedder.encode([query]), dtype="float32")
        D, I = self.index.search(qv, k)
        ids = [int(x) for x in I[0].tolist() if x != -1]
        if not ids:
            return []
        by_id = _map_faiss_ids_to_rids(self.db_path, ids)
        # Minimal docs for downstream enrichment in tools/search.py
        out = [{"id": rid} for fid in ids if (rid := by_id.get(fid))]
        return out

def clear_caches():
    get_index.cache_clear()
    get_embedder.cache_clear()
