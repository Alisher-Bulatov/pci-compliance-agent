#!/usr/bin/env python3
"""
view_db.py — Inspect the PCI SQLite content (counts, preview, missing parents, optional tree).

Usage:
  python scripts/view_db.py [--tree] [--check 1,10,11]
"""

import argparse, sqlite3
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_FILE = ROOT / "data" / "pci_requirements.db"

def level_of(code: str):
    parts = code.split(".")
    if len(parts) == 1: return "Requirement"
    if len(parts) == 2: return "Section"
    return "Subsection"

def parent_of(code: str):
    parts = code.split(".")
    if len(parts) == 1: return None
    if len(parts) == 2: return parts[0]
    return ".".join(parts[:2])

def naturalsort(code: str):
    return [int(x) if x.isdigit() else x for x in code.split(".")]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", action="store_true")
    ap.add_argument("--check", default="")
    args = ap.parse_args()

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(requirements)")
    cols = [r[1] for r in cur.fetchall()]
    needed = {"id","text"}
    if not needed.issubset(set(cols)):
        raise SystemExit(f"requirements table missing needed columns: {needed} (have {cols})")

    cur.execute("SELECT id, text, COALESCE(level,''), COALESCE(parent_id,'') FROM requirements ORDER BY id")
    rows = [{"id":r[0],"text":r[1],"level":r[2] or level_of(r[0]),"parent":r[3] or parent_of(r[0])} for r in cur.fetchall()]
    conn.close()

    counts = defaultdict(int)
    for r in rows:
        counts[r["level"]] += 1

    print("== Row counts by level ==")
    for k in ("Requirement","Section","Subsection"):
        print(f"{k:12s}: {counts.get(k,0)}")

    print("\n== Preview (first 50) ==")
    for r in rows[:50]:
        print((r["id"], r["text"]))

    codes = {r["id"] for r in rows}
    missing = [(r["id"], r["parent"]) for r in rows if r["parent"] and r["parent"] not in codes]
    if missing:
        print("\n== Missing parent chains ==")
        for c,p in missing[:50]:
            print(f"{c} -> {p}")
    else:
        print("\n== Parent chains OK ==")

    if args.tree:
        only = [x.strip() for x in args.check.split(",") if x.strip()]
        children = defaultdict(list)
        by_id = {r["id"]: r for r in rows}
        for r in rows:
            children[r["parent"]].append(r["id"])
        roots = [c for c in children[None]]
        if only:
            roots = [r for r in roots if r.split(".")[0] in only]
        for req in sorted(roots, key=naturalsort):
            print(f"{req} — {by_id[req]['text']}")
            for sec in sorted(children.get(req, []), key=naturalsort):
                print(f"  {sec} — {by_id[sec]['text']}")
                for sub in sorted(children.get(sec, []), key=naturalsort):
                    print(f"    {sub} — {by_id[sub]['text']}")

if __name__ == "__main__":
    main()
