import faiss
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer

class PCIDocumentRetriever:
    def __init__(self, index_path="data/pci_index.faiss", mapping_path="data/mapping.pkl"):
        self.index = faiss.read_index(index_path)
        self.mapping = pickle.load(open(mapping_path, "rb"))
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")

    def retrieve(self, query, k=3):
        query_vec = self.embedder.encode([query])
        D, I = self.index.search(np.array(query_vec).astype("float32"), k)
        results = []

        for idx in I[0]:
            if idx == -1:
                continue
            doc = self.mapping.get(idx)
            if doc:
                results.append(doc)

        return results
