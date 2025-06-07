import pickle

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


class PCIDocumentRetriever:
    def __init__(
        self, index_path="data/pci_index.faiss", mapping_path="data/mapping.pkl"
    ):
        self.index = faiss.read_index(index_path)
        with open(mapping_path, "rb") as f:
            self.mapping = pickle.load(f)
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")

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
