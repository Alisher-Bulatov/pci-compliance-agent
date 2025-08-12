# verify_index_vs_db.py — sanity-check FAISS labels vs SQLite mapping + requirements
import sqlite3
from pathlib import Path
import faiss

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
DB_FILE = DATA_DIR / "pci_requirements.db"
INDEX_FILE = DATA_DIR / "pci_index.faiss"

def main():
    if not DB_FILE.exists():
        print(f"❌ Missing DB: {DB_FILE}")
        return
    if not INDEX_FILE.exists():
        print(f"❌ Missing index: {INDEX_FILE}")
        return

    # Read labels from FAISS (via Range search to get count)
    index = faiss.read_index(str(INDEX_FILE))
    n = index.ntotal
    # Note: labels aren’t directly enumerable; we check mapping table cardinality and referential integrity.
    conn = sqlite3.connect(str(DB_FILE))
    cur = conn.cursor()
    map_count = cur.execute("SELECT COUNT(*) FROM faiss_map").fetchone()[0]
    req_count = cur.execute("SELECT COUNT(*) FROM requirements").fetchone()[0]

    print(f"FAISS ntotal={n}, faiss_map rows={map_count}, requirements rows={req_count}")

    # Check some samples are valid joins
    rows = cur.execute("SELECT faiss_id, rid FROM faiss_map ORDER BY faiss_id LIMIT 10").fetchall()
    missing = []
    for fid, rid in rows:
        ok = cur.execute("SELECT 1 FROM requirements WHERE id = ? LIMIT 1", (rid,)).fetchone()
        if not ok:
            missing.append((fid, rid))

    if missing:
        print(f"⚠ Missing requirements for {len(missing)} faiss_map rows (first few): {missing[:5]}")
    elif n != map_count:
        print("⚠ FAISS ntotal and faiss_map count differ. Rebuild index/mapping.")
    else:
        print("✅ FAISS labels and SQLite mapping look consistent.")

    conn.close()

if __name__ == "__main__":
    main()
