import pickle
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

with open(DATA_DIR / "mapping.pkl", "rb") as f:
    requirement_map = pickle.load(f)

def get_requirement_text(requirement_id: str) -> str:
    for text in requirement_map.values():
        if requirement_id.lower() in text.lower():
            return text
    return f"Requirement {requirement_id} not found."
