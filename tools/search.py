"""Search PCI DSS requirements by topic using the user's own words as the query.

Enriches top-K FAISS hits with authoritative text/tags from SQLite (single source of truth).
If enrichment is disabled, falls back to FAISS mapping text/snippet when present.
"""

from typing import Literal, Optional, List, Dict, Any
import os
import sqlite3
from pathlib import Path

from pydantic import BaseModel, Field

from retrieval.retriever import PCIDocumentRetriever
from agent.models.requirement import RequirementEntry, RequirementOutput


class InputSchema(BaseModel):
    query: str
    k: Optional[int] = Field(
        default=None,
        description="Number of results to return (defaults from env SEARCH_TOP_K or 8).",
    )


class OutputSchema(RequirementOutput):
    tool_name: Literal["search"]


retriever = PCIDocumentRetriever()

DEFAULT_K = int(os.getenv("SEARCH_TOP_K", "8"))
ENRICH = os.getenv("SEARCH_ENRICH_WITH_SQLITE", "1").lower() not in {"0", "false", "no"}
ENRICH_MAX = int(os.getenv("SEARCH_ENRICH_MAX", "6"))  # cap enrichment fanout

# Resolve DB relative to repo root (../data/pci_requirements.db)
DB_FILE = Path(__file__).resolve().parents[1] / "data" / "pci_requirements.db"


def _normalize_doc(doc: Dict[str, Any]) -> Dict[str, Any] | None:
    """Return minimal normalized dict {id, text?, tags?} from retriever doc."""
    if not isinstance(doc, dict):
        return None
    rid = doc.get("id")
    if not isinstance(rid, str) or not rid.strip():
        return None
    out = {"id": rid.strip()}
    # Optional fields from FAISS mapping (may be snippet/full depending on build)
    if isinstance(doc.get("text"), str):
        out["text"] = doc["text"].strip()
    if isinstance(doc.get("snippet"), str):
        out["snippet"] = doc["snippet"].strip()
    tags = doc.get("tags")
    if isinstance(tags, list):
        out["tags"] = tags
    return out


def _enrich_from_sqlite(ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """Batch fetch text/tags from SQLite; returns {id: {text, tags}}."""
    out: Dict[str, Dict[str, Any]] = {}
    if not ids or not DB_FILE.exists():
        return out
    try:
        conn = sqlite3.connect(str(DB_FILE))
        cur = conn.cursor()
        qmarks = ",".join(["?"] * len(ids))
        rows = cur.execute(
            f"SELECT id, text, tags FROM requirements WHERE id IN ({qmarks})",
            ids,
        ).fetchall()
        conn.close()
    except Exception:
        return out
    for rid, text, tags in rows:
        tag_list = [t for t in (tags or "").split(",") if t]
        out[str(rid)] = {"text": str(text), "tags": tag_list}
    return out


def main(input_data: InputSchema) -> OutputSchema:
    q = (input_data.query or "").strip()
    k = input_data.k or DEFAULT_K

    if not q:
        return OutputSchema(
            status="error",
            tool_name="search",
            error="Empty query.",
            result=[],
            meta={"query": q, "k": k, "enriched": False},
        )

    # Step 1: FAISS recall
    try:
        docs = retriever.retrieve(q, k=k)
    except Exception as e:
        return OutputSchema(
            status="error",
            tool_name="search",
            error=f"retriever failure: {e}",
            result=[],
            meta={"query": q, "k": k, "enriched": False},
        )

    hits: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for d in docs or []:
        nd = _normalize_doc(d)
        if nd and nd["id"] not in seen:
            hits.append(nd)
            seen.add(nd["id"])

    if not hits:
        return OutputSchema(
            status="not_found",
            tool_name="search",
            result=[],
            meta={"query": q, "k": k, "enriched": False},
        )

    # Step 2: Optional SQLite enrichment for authoritative text/tags
    enriched = False
    by_id: Dict[str, Dict[str, Any]] = {}
    if ENRICH:
        ids = [h["id"] for h in hits[:ENRICH_MAX]]
        by_id = _enrich_from_sqlite(ids)
        enriched = bool(by_id)

    # Step 3: Build RequirementEntry results (prefer SQLite text; fallback to FAISS text/snippet)
    entries: List[RequirementEntry] = []
    for h in hits[:k]:
        rid = h["id"]
        src = by_id.get(rid, {})
        text = src.get("text") or h.get("text") or h.get("snippet") or ""
        tags = src.get("tags") or h.get("tags") or []
        if not text:
            # Skip malformed rows without any text
            continue
        entries.append(RequirementEntry(id=rid, text=text, tags=tags))

    if not entries:
        return OutputSchema(
            status="not_found",
            tool_name="search",
            result=[],
            meta={"query": q, "k": k, "enriched": enriched},
        )

    return OutputSchema(
        status="success",
        tool_name="search",
        result=entries,
        meta={"query": q, "k": k, "enriched": enriched, "source": "sqlite" if enriched else "faiss"},
    )

