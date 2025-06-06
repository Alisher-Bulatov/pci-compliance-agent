import pickle

with open("data/mapping.pkl", "rb") as f:
    requirement_map = pickle.load(f)

def main(requirement_id: str) -> dict:
    for entry in requirement_map.values():
        if isinstance(entry, dict) and entry.get("id", "").lower() == requirement_id.lower():
            return entry
    return {
        "id": requirement_id,
        "text": f"Requirement {requirement_id} not found.",
        "tags": []
    }
