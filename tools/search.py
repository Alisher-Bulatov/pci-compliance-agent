"""Search PCI DSS requirements by topic using FAISS (ANN) + SQLite fallback."""

from __future__ import annotations
from typing import Literal, Optional, List, Dict, Any
import os
import re
import sqlite3
from pathlib import Path

from pydantic import BaseModel, Field, root_validator

from retrieval.retriever import PCIDocumentRetriever
from agent.models.requirement import RequirementEntry

# ---------------- Input/Output ----------------

class InputSchema(BaseModel):
    q: Optional[str] = Field(None)
    query: Optional[str] = Field(None)
    k: Optional[int] = Field(default=None)
    enrich: Optional[bool] = Field(default=None)

    @root_validator(pre=True)
    def _coalesce_q(cls, values):
        if not values.get("q") and values.get("query"):
            values["q"] = values["query"]
        return values

class RequirementOutput(BaseModel):
    status: Literal["success", "not_found"]
    tool_name: Literal["search"]
    result: List[RequirementEntry]
    meta: Dict[str, Any] | None = None

class OutputSchema(RequirementOutput):
    tool_name: Literal["search"]

# ---------------- Config ----------------

retriever = PCIDocumentRetriever()
DEFAULT_K = int(os.getenv("SEARCH_TOP_K", "8"))
ENRICH_DEFAULT = os.getenv("SEARCH_ENRICH_WITH_SQLITE", "1").lower() not in {"0","false","no"}
ENRICH_MAX = int(os.getenv("SEARCH_ENRICH_MAX", "6"))

DEFAULT_DB_FILE = Path("data/pci_requirements.db")

STOP = {
    "the","a","an","and","or","of","to","for","in","on","with","by","as","is","are","be",
    "that","this","these","those","from","at","into","it","its","their","your","my","our",
    "about","over","under","between","across","than","then"
}

# ---------------- Helpers ----------------

def _db_path() -> Path:
    override = (os.getenv("DB_LOCAL_PATH") or os.getenv("SQLITE_DB_PATH") or "").strip()
    return Path(override) if override else DEFAULT_DB_FILE

def _connect_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_db_path()))
    conn.row_factory = sqlite3.Row
    return conn

def _normalize_doc(doc: Dict[str, Any]) -> Dict[str, Any] | None:
    if not isinstance(doc, dict):
        return None
    rid = str(doc.get("id") or "").strip().rstrip(".")
    if not rid:
        return None
    out: Dict[str, Any] = {"id": rid}
    if isinstance(doc.get("text"), str) and doc["text"].strip():
        out["text"] = doc["text"].strip()
    tags = doc.get("tags")
    if isinstance(tags, list):
        out["tags"] = tags
    return out

def _enrich_with_sqlite(ids: List[str]) -> Dict[str, Dict[str, Any]]:
    if not ids:
        return {}
    placeholders = ",".join("?" for _ in ids)
    sql = f"SELECT id, text, COALESCE(tags,'') AS tags FROM requirements WHERE id IN ({placeholders})"
    with _connect_db() as conn:
        rows = conn.execute(sql, ids).fetchall()
    out: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        out[r["id"]] = {
            "id": r["id"],
            "text": r["text"] or "",
            "tags": [t for t in (r["tags"] or "").split(",") if t],
        }
    return out

def _keywords(q: str) -> List[str]:
    toks = re.findall(r"[A-Za-z0-9]+", q.lower())
    toks = [t for t in toks if t not in STOP]
    # very light stemming for common cases
    stemmed: List[str] = []
    for t in toks:
        if t.endswith("ions"):
            t = t[:-1]  # protections -> protection
        if t.endswith("ing") and len(t) > 5:
            t = t[:-3]  # phishing -> phish
        if t.endswith("ed") and len(t) > 4:
            t = t[:-2]  # protected -> protect
        if t.endswith("s") and len(t) > 4:
            t = t[:-1]  # mechanisms -> mechanism
        stemmed.append(t)
    # make unique but keep order
    seen = set()
    uniq: List[str] = []
    for t in stemmed:
        if t and t not in seen:
            uniq.append(t)
            seen.add(t)
    return uniq

def _sqlite_keyword_fallback_smart(q: str, k: int) -> List[Dict[str, Any]]:
    """
    Progressive relaxation:
      1) AND all tokens (text OR title)
      2) If 0, require any 2 tokens (pairwise AND)
      3) If 0, OR across tokens
    Each token uses '%' suffix wildcard for light stemming.
    """
    kws = _keywords(q)
    fields = ["text", "title"]  # search both
    if not kws:
        like = f"%{q.replace('%','')}%"
        sql = f"SELECT id, text, '' AS tags FROM requirements WHERE text LIKE ? OR title LIKE ? ORDER BY id LIMIT ?"
        try:
            with _connect_db() as conn:
                rows = conn.execute(sql, (like, like, k)).fetchall()
            return [{"id": r["id"], "text": r["text"], "tags": []} for r in rows]
        except Exception:
            return []

    def run_sql(where_parts: List[str], params: List[str], limit: int) -> List[Dict[str, Any]]:
        sql = f"SELECT id, text, COALESCE(tags,'') AS tags FROM requirements WHERE {' AND '.join(where_parts)} ORDER BY id LIMIT ?"
        with _connect_db() as conn:
            rows = conn.execute(sql, params + [limit]).fetchall()
        return [{"id": r["id"], "text": r["text"], "tags": [t for t in (r["tags"] or '').split(',') if t]} for r in rows]

    # 1) AND all tokens across (text OR title)
    where = []
    params: List[str] = []
    for kw in kws:
        clause = "(" + " OR ".join([f"{f} LIKE ?" for f in fields]) + ")"
        where.append(clause)
        like = f"%{kw}%"
        params.extend([like] * len(fields))
    try:
        hits = run_sql(where, params, k)
        if hits:
            return hits
    except Exception:
        pass

    # 2) Any 2 tokens (pairwise AND)
    if len(kws) >= 2:
        for i in range(len(kws)):
            for j in range(i+1, len(kws)):
                where = []
                params = []
                for kw in (kws[i], kws[j]):
                    clause = "(" + " OR ".join([f"{f} LIKE ?" for f in fields]) + ")"
                    where.append(clause)
                    like = f"%{kw}%"
                    params.extend([like] * len(fields))
                try:
                    hits = run_sql(where, params, k)
                    if hits:
                        return hits
                except Exception:
                    pass

    # 3) OR across tokens
    ors = []
    params = []
    for kw in kws:
        ors.extend([f"{f} LIKE ?" for f in fields])
        params.extend([f"%{kw}%"] * len(fields))
    sql = f"SELECT id, text, COALESCE(tags,'') AS tags FROM requirements WHERE {' OR '.join(ors)} ORDER BY id LIMIT ?"
    try:
        with _connect_db() as conn:
            rows = conn.execute(sql, params + [k]).fetchall()
        return [{"id": r["id"], "text": r["text"], "tags": [t for t in (r['tags'] or '').split(',') if t]} for r in rows]
    except Exception:
        return []

# ---------------- Tool entry ----------------

def run(params: Dict[str, Any]) -> OutputSchema:
    q = (params or {}).get("q") or (params or {}).get("query") or ""
    q = (q or "").strip()
    k = (params or {}).get("k") or DEFAULT_K
    do_enrich = (params or {}).get("enrich")
    if do_enrich is None:
        do_enrich = ENRICH_DEFAULT

    if not q:
        return OutputSchema(status="not_found", tool_name="search", result=[], meta={"reason": "empty_query"})

    # 1) Try ANN
    ann_docs: List[Dict[str, Any]] = []
    retriever_error = None
    try:
        ann_docs = retriever.search(q, k=k)
    except Exception as e:
        retriever_error = f"{e.__class__.__name__}: {e}"

    if not ann_docs:
        # 2) Fallback SQLite
        sql_hits = _sqlite_keyword_fallback_smart(q, k)
        entries: List[RequirementEntry] = []
        for d in sql_hits:
            nd = _normalize_doc(d)
            if nd:
                entries.append(RequirementEntry(id=nd["id"], text=nd.get("text", ""), tags=nd.get("tags", [])))
        if entries:
            meta = {"query": q, "k": k, "source": "sqlite_like_fallback"}
            if retriever_error:
                meta["retriever_error"] = retriever_error
            return OutputSchema(status="success", tool_name="search", result=entries, meta=meta)
        meta = {"query": q, "k": k}
        if retriever_error:
            meta["retriever_error"] = retriever_error
        return OutputSchema(status="not_found", tool_name="search", result=[], meta=meta)

    # 3) Enrich FAISS hits via SQLite (best effort)
    ids = [str(d.get("id")) for d in ann_docs if d.get("id")]
    entries: List[RequirementEntry] = []
    if do_enrich:
        by_id = _enrich_with_sqlite(ids[:ENRICH_MAX])
        for rid in ids[:k]:
            src = by_id.get(rid, {})
            text = src.get("text") or ""
            tags = src.get("tags") or []
            if text:
                entries.append(RequirementEntry(id=rid, text=text, tags=tags))
    if not entries:
        # Just return IDs if SQLite was unavailable
        entries = [RequirementEntry(id=rid, text="", tags=[]) for rid in ids[:k]]

    return OutputSchema(status="success", tool_name="search", result=entries, meta={"query": q, "k": k, "source": "faiss"})
