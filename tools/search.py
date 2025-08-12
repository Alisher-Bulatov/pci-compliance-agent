"""Search PCI DSS requirements by topic using the user's words.

Pipeline:
1) FAISS ANN (via retrieval.PCIDocumentRetriever.search)
2) Enrich with SQLite (authoritative text/tags)
3) If FAISS yields nothing, fallback to SQLite LIKE
"""

from __future__ import annotations
from typing import Literal, Optional, List, Dict, Any
import os
import sqlite3
from pathlib import Path

from pydantic import BaseModel, Field, root_validator

from retrieval.retriever import PCIDocumentRetriever
from agent.models.requirement import RequirementEntry, RequirementOutput


# ---- Input / Output Schemas -------------------------------------------------

class InputSchema(BaseModel):
    # Accept both "q" and "query"
    q: Optional[str] = Field(None, description="User search query (preferred)")
    query: Optional[str] = Field(None, description="Alias for q")
    k: Optional[int] = Field(
        default=None,
        description="Number of results to return (defaults from env SEARCH_TOP_K or 8).",
    )
    enrich: Optional[bool] = Field(
        default=None,
        description="Enrich with SQLite content (defaults from env SEARCH_ENRICH_WITH_SQLITE).",
    )

    @root_validator(pre=True)
    def _coalesce_q(cls, values):
        # allow old callers that send only {"query": "..."}
        if not values.get("q") and values.get("query"):
            values["q"] = values["query"]
        return values


class OutputSchema(RequirementOutput):
    tool_name: Literal["search"]


# ---- Config / Globals -------------------------------------------------------

retriever = PCIDocumentRetriever()

DEFAULT_K = int(os.getenv("SEARCH_TOP_K", "8"))
ENRICH_DEFAULT = os.getenv("SEARCH_ENRICH_WITH_SQLITE", "1").lower() not in {"0", "false", "no"}
ENRICH_MAX = int(os.getenv("SEARCH_ENRICH_MAX", "6"))  # cap enrichment fanout

# Resolve DB relative to repo root (../data/pci_requirements.db),
# but honor service env overrides used elsewhere.
DEFAULT_DB_FILE = Path(__file__).resolve().parents[1] / "data" / "pci_requirements.db"


# ---- Helpers ----------------------------------------------------------------

def _db_path() -> Path:
    override = (os.getenv("DB_LOCAL_PATH") or os.getenv("SQLITE_DB_PATH") or "").strip()
    return Path(override) if override else DEFAULT_DB_FILE

def _connect_db() -> sqlite3.Connection:
    return sqlite3.connect(str(_db_path()))

def _normalize_doc(doc: Dict[str, Any]) -> Dict[str, Any] | None:
    """Return minimal normalized dict {id, text?, tags?}."""
    if not isinstance(doc, dict):
        return None
    rid = str(doc.get("id") or "").strip().rstrip(".")
    if not rid:
        return None
    out: Dict[str, Any] = {"id": rid}
    # If the retriever ever returns text/snippet/tags, keep them, but they are optional.
    if isinstance(doc.get("text"), str) and doc["text"].strip():
        out["text"] = doc["text"].strip()
    if isinstance(doc.get("snippet"), str) and doc["snippet"].strip():
        out["snippet"] = doc["snippet"].strip()
    tags = doc.get("tags")
    if isinstance(tags, list):
        out["tags"] = tags
    return out

def _enrich_with_sqlite(ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """Batch fetch text/tags from SQLite; returns {id: {text, tags}}."""
    out: Dict[str, Dict[str, Any]] = {}
    if not ids:
        return out
    try:
        qmarks = ",".join("?" for _ in ids)
        sql = f"SELECT id, text, tags FROM requirements WHERE id IN ({qmarks})"
        with _connect_db() as conn:
            rows = conn.execute(sql, ids).fetchall()
        for rid, text, tags in rows:
            tag_list = [t for t in (tags or "").split(",") if t]
            out[str(rid)] = {"text": str(text or ""), "tags": tag_list}
    except Exception:
        # Silent fail to enrichment; core search still returns IDs
        pass
    return out

def _sqlite_keyword_fallback(q: str, k: int) -> List[Dict[str, Any]]:
    """Simple LIKE fallback when FAISS returns nothing."""
    like = f"%{q.replace('%','')}%"
    sql = """
    SELECT id, text, tags
    FROM requirements
    WHERE text LIKE ?
    ORDER BY id
    LIMIT ?
    """
    try:
        with _connect_db() as conn:
            rows = conn.execute(sql, (like, k)).fetchall()
        return [{"id": r[0], "text": r[1], "tags": [t for t in (r[2] or '').split(',') if t]} for r in rows]
    except Exception:
        return []


# ---- Entry point required by dispatcher -------------------------------------

def run(payload: Dict[str, Any]) -> OutputSchema:
    # Validate input
    try:
        inp = InputSchema(**payload)
    except Exception as e:
        return OutputSchema(
            status="error",
            tool_name="search",
            error=f"bad_input: {e}",
            result=[],
            meta={"raw_payload": payload},
        )

    q = (inp.q or "").strip()
    if not q:
        return OutputSchema(
            status="error",
            tool_name="search",
            error="empty_query",
            result=[],
            meta={},
        )

    k = inp.k if inp.k is not None else DEFAULT_K
    do_enrich = ENRICH_DEFAULT if inp.enrich is None else bool(inp.enrich)

    # 1) ANN search via FAISS (returns [{"id": rid}, ...])
    try:
        ann_docs = retriever.search(q, k=k)
    except Exception as e:
        # If retriever fails (e.g., FAISS not available), still try SQLite fallback.
        ann_docs = []
        retriever_error = str(e)
    else:
        retriever_error = None

    if not ann_docs:
        # 2) Fallback: simple LIKE over SQLite text
        sql_hits = _sqlite_keyword_fallback(q, k)
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
        # Nothing at all
        meta = {"query": q, "k": k}
        if retriever_error:
            meta["retriever_error"] = retriever_error
        return OutputSchema(status="not_found", tool_name="search", result=[], meta=meta)

    # 3) Enrich via SQLite for authoritative text/tags
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
        if entries:
            return OutputSchema(
                status="success",
                tool_name="search",
                result=entries,
                meta={"query": q, "k": k, "source": "faiss+sqlite"},
            )

    # Fallback to raw IDs if enrichment off/empty (no text means UI will fetch with get)
    entries = [RequirementEntry(id=rid) for rid in ids[:k]]
    return OutputSchema(
        status="success",
        tool_name="search",
        result=entries,
        meta={"query": q, "k": k, "source": "faiss_only"},
    )


# ---- Optional: CLI for local testing ----------------------------------------

def main():
    import argparse, json as _json
    ap = argparse.ArgumentParser()
    ap.add_argument("query", help="search query")
    ap.add_argument("-k", type=int, default=DEFAULT_K)
    ap.add_argument("--no-enrich", action="store_true")
    args = ap.parse_args()
    out = run({"q": args.query, "k": args.k, "enrich": (not args.no_enrich)})
    print(_json.dumps(out.dict(), indent=2))

if __name__ == "__main__":
    main()
