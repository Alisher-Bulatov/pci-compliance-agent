import sqlite3
from pathlib import Path

# Define path to the SQLite DB
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "pci_requirements.db"

# Connect and query
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("SELECT id, text FROM requirements ORDER BY id")
rows = cursor.fetchall()
conn.close()

# Print all requirements
for row in rows:
    print(row)
