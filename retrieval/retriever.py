import pickle
import threading
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from functools import lru_cache

# Thread locks to prevent race condition on first load
_index_lock = threading.Lock()
_mapping_lock = threading.Lock()
_embedder_lock = threading.Lock()


@lru_cache(maxsize=1)
def get_index(path="data/pci_index.faiss"):
    with _index_lock:
        return faiss.read_index(path)


@lru_cache(maxsize=1)
def get_mapping(path="data/mapping.pkl"):
    with _mapping_lock:
        with open(path, "rb") as f:
            return pickle.load(f)


@lru_cache(maxsize=1)
def get_embedder():
    with _embedder_lock:
        return SentenceTransformer("all-MiniLM-L6-v2")


class PCIDocumentRetriever:
    def __init__(
        self, index_path="data/pci_index.faiss", mapping_path="data/mapping.pkl"
    ):
        self.index = get_index(index_path)
        self.mapping = get_mapping(mapping_path)
        self.embedder = get_embedder()

    def retrieve(self, query, k=3):
        query_vec = self.embedder.encode([query])
        _, indices = self.index.search(np.array(query_vec).astype("float32"), k)
        results = []

        for idx in indices[0]:
            if idx == -1:
                continue
            doc = self.mapping.get(idx)
            if doc:
                results.append(doc)

        return results


def clear_caches():
    get_index.cache_clear()
    get_mapping.cache_clear()
    get_embedder.cache_clear()
