import faiss
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer

chunks = []
with open("data/pci_chunks.txt", "r") as f:
    chunks = [line.strip() for line in f.readlines()]

model = SentenceTransformer("all-MiniLM-L6-v2")
vectors = model.encode(chunks)

index = faiss.IndexFlatL2(vectors.shape[1])
index.add(np.array(vectors).astype("float32"))

with open("data/mapping.pkl", "wb") as f:
    pickle.dump({i: chunk for i, chunk in enumerate(chunks)}, f)

faiss.write_index(index, "data/pci_index.faiss")
print("✅ RAG index built.")