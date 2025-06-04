import faiss
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer

INDEX_PATH = "data/pci_index.faiss"
MAPPING_PATH = "data/mapping.pkl"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
TOP_K = 10  # Get more candidates for better reranking

# Simple tag extraction
def extract_query_tags(query):
    lowered = query.lower()
    tags = []
    if any(word in lowered for word in ["encrypt", "crypto", "key"]):
        tags.append("encryption")
    if any(word in lowered for word in ["auth", "password", "login"]):
        tags.append("authentication")
    if any(word in lowered for word in ["store", "retain", "database"]):
        tags.append("storage")
    if any(word in lowered for word in ["firewall", "network", "router"]):
        tags.append("network")
    if "compliance" in lowered or "audit" in lowered:
        tags.append("compliance")
    return tags

def search_by_topic(query):
    index = faiss.read_index(INDEX_PATH)
    with open(MAPPING_PATH, "rb") as f:
        mapping = pickle.load(f)
    embedder = SentenceTransformer(EMBEDDING_MODEL)

    query_vec = embedder.encode([query])
    D, I = index.search(np.array(query_vec), TOP_K)

    query_tags = set(extract_query_tags(query))
    candidates = []

    for i in I[0]:
        entry = mapping.get(i)
        if not entry:
            continue
        entry_tags = set(entry.get("tags", []))
        overlap_score = len(entry_tags & query_tags)
        candidates.append((entry, overlap_score))

    # Sort: first by tag overlap, then fallback to embedding proximity
    candidates.sort(key=lambda x: x[1], reverse=True)

    # Return as structured list (for MCP or rerouting)
    return [
        {
            "id": entry["id"],
            "text": entry["text"],
            "tags": entry["tags"]
        }
        for entry, _ in candidates[:5]  # Limit final output
    ]

# CLI test mode
if __name__ == "__main__":
    query = input("Enter your topic query: ")
    results = search_by_topic(query)
    for r in results:
        print(f"Requirement {r['id']}: {r['text']} [tags: {', '.join(r['tags'])}]\n")
