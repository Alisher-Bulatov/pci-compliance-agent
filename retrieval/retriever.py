import faiss
import pickle
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent.parent


class PCIDocumentRetriever:
    def __init__(self, index_path="data/pci_index.faiss", mapping_path="data/mapping.pkl"):
        index_path = BASE_DIR / index_path
        mapping_path = BASE_DIR / mapping_path
        self.index = faiss.read_index(str(index_path))
        with open(mapping_path, "rb") as f:
            self.mapping = pickle.load(f)
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")

    def retrieve(self, query, k=3):
        query_vec = self.embedder.encode([query])
        D, I = self.index.search(np.array(query_vec).astype("float32"), k)
        return [self.mapping[i] for i in I[0]]
