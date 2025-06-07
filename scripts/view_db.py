import sqlite3

conn = sqlite3.connect("data/pci_requirements.db")
cursor = conn.cursor()
cursor.execute("SELECT id, text FROM requirements WHERE id IN ('1.1.2', '12.5.1')")
results = cursor.fetchall()
conn.close()

for row in results:
    print(row)
