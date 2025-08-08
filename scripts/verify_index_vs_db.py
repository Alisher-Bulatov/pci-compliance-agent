
# verify_index_vs_db.py — sanity-check FAISS mapping vs SQLite DB
import pickle, sqlite3
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent  # go up from /scripts
DATA_DIR = ROOT_DIR / "data"
DB_FILE = DATA_DIR / "pci_requirements.db"
MAPPING_FILE = DATA_DIR / "mapping.pkl"

DATA_DIR.mkdir(parents=True, exist_ok=True)

def main():
    if not DB_FILE.exists():
        print(f"❌ Missing DB: {DB_FILE}")
        return
    if not MAPPING_FILE.exists():
        print(f"❌ Missing mapping: {MAPPING_FILE}")
        return

    with open(MAPPING_FILE, "rb") as f:
        mapping = pickle.load(f)
    faiss_ids = {entry["id"] for entry in mapping.values() if isinstance(entry, dict) and "id" in entry}

    conn = sqlite3.connect(str(DB_FILE))
    cur = conn.cursor()
    cur.execute("SELECT id FROM requirements")
    db_ids = {rid.strip().rstrip('.') for (rid,) in cur.fetchall()}
    conn.close()

    only_in_faiss = sorted(faiss_ids - db_ids)
    only_in_db = sorted(db_ids - faiss_ids)

    if not only_in_faiss and not only_in_db:
        print("✅ Mapping and SQLite IDs are in sync.")
    else:
        if only_in_faiss:
            print(f"⚠ IDs only in FAISS mapping ({len(only_in_faiss)}): {only_in_faiss[:20]}{' ...' if len(only_in_faiss)>20 else ''}")
        if only_in_db:
            print(f"⚠ IDs only in SQLite DB ({len(only_in_db)}): {only_in_db[:20]}{' ...' if len(only_in_db)>20 else ''}")

if __name__ == "__main__":
    main()

