import re
import pickle
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# === Configuration ===
SOURCE_FILE = "data/pci_chunks.txt"
INDEX_FILE = "data/pci_index.faiss"
MAPPING_FILE = "data/mapping.pkl"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# === Simple tag rules ===
TAG_KEYWORDS = {
    "encryption": [
        "encrypt",
        "cryptographic",
        "cipher",
        "key management",
        "decryption",
        "protect cardholder data",
    ],
    "authentication": [
        "authentication",
        "auth",
        "login",
        "password",
        "PIN",
        "biometric",
    ],
    "network": ["firewall", "router", "network", "packet", "traffic"],
    "compliance": ["compliance", "audit", "responsibility"],
    "storage": ["store", "storage", "retain", "save", "database"],
}


def extract_tags(text: str) -> list[str]:
    tag_set = set()
    lowered = text.lower()
    for tag, keywords in TAG_KEYWORDS.items():
        if any(kw in lowered for kw in keywords):
            tag_set.add(tag)
    return list(tag_set)


def extract_id_and_text(raw_line: str) -> tuple[str | None, str | None]:
    match = re.match(r"Requirement (\d[\d.]*)\s*:\s*(.+)", raw_line)
    if match:
        return match.group(1), match.group(2)
    return None, None


# === Load and parse data ===
source_path = Path(SOURCE_FILE)
lines = [
    line.strip()
    for line in source_path.read_text(encoding="utf-8").splitlines()
    if line.strip()
]

mapping = {}
texts = []
for content in lines:
    req_id, req_text = extract_id_and_text(content)
    if not req_id:
        continue
    tag_list = extract_tags(req_text)
    entry = {"id": req_id, "text": req_text, "tags": tag_list}
    mapping[len(mapping)] = entry
    texts.append(f"{req_id}: {req_text}")

# === Embed and index ===
embedder = SentenceTransformer(EMBEDDING_MODEL)
embeddings = np.asarray(embedder.encode(texts, show_progress_bar=True), dtype="float32")
embedding_dim = embeddings.shape[1]

index = faiss.IndexFlatL2(embedding_dim)
# pylint: disable=no-value-for-parameter
index.add(embeddings)

# === Save outputs ===
faiss.write_index(index, INDEX_FILE)
with open(MAPPING_FILE, "wb") as f:
    pickle.dump(mapping, f)

print(f"✅ Rebuilt index with {len(mapping)} entries.")
