import json
import pickle
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# === Configuration ===
JSON_FILE = Path("data/pciRequirements.json")
INDEX_FILE = Path("data/pci_index.faiss")
MAPPING_FILE = Path("data/mapping.pkl")
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


def parse_json_records(obj: dict) -> list[tuple[str, str]]:
    """
    Parse key/value pairs from pciRequirements.json -> list of (id, text).
    Keys can be 'Requirement X' or 'Section X.Y'.
    """
    records = []
    for key, val in obj.items():
        if not isinstance(val, str):
            continue
        parts = key.split(maxsplit=1)
        if len(parts) < 2:
            continue
        req_id = parts[1].strip()
        text = val.strip()
        if req_id and text:
            records.append((req_id, text))
    return records


# === Load data from JSON ===
if not JSON_FILE.exists():
    raise FileNotFoundError(f"❌ JSON file not found: {JSON_FILE}")

data = json.loads(JSON_FILE.read_text(encoding="utf-8"))
records = parse_json_records(data)

if not records:
    raise ValueError("❌ No valid requirement records found in JSON.")

# Remove duplicate IDs while preserving order
seen = set()
deduped = []
for req_id, req_text in records:
    if req_id in seen:
        continue
    seen.add(req_id)
    deduped.append((req_id, req_text))

# Build mapping and text list
mapping = {}
texts = []
for i, (req_id, req_text) in enumerate(deduped):
    tag_list = extract_tags(req_text)
    mapping[i] = {"id": req_id, "text": req_text, "tags": tag_list}
    texts.append(f"{req_id}: {req_text}")

# === Embed and index ===
embedder = SentenceTransformer(EMBEDDING_MODEL)
embeddings = np.asarray(embedder.encode(texts, show_progress_bar=True), dtype="float32")
embedding_dim = embeddings.shape[1]

index = faiss.IndexFlatL2(embedding_dim)
index.add(embeddings)

# === Save outputs ===
INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
faiss.write_index(index, str(INDEX_FILE))
with open(MAPPING_FILE, "wb") as f:
    pickle.dump(mapping, f)

print(f"✅ Rebuilt index with {len(mapping)} entries from JSON.")
