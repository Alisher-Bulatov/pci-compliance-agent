import json
import re
from typing import List, Any, Dict

MAX_IDS = 50

# 1..12 followed by up to 3 dotted segments (1–2 digits each)
_ID_RX = re.compile(r"\b(1[0-2]|[1-9])(?:\.(\d{1,2})){0,3}\b")

def _is_valid_pci_id(s: str) -> bool:
    if not s or " " in s:
        return False
    return _ID_RX.fullmatch(s.strip()) is not None

def _dedupe(ids: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for x in ids:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

def _extract_ids_loose(payload: str) -> List[str]:
    if not payload:
        return []
    found = [m.group(0) for m in _ID_RX.finditer(payload)]
    valid = [sid for sid in found if _is_valid_pci_id(sid)]
    return _dedupe(valid)[:MAX_IDS]

def _parse_compact(text: str) -> Any:
    s = (text or "").strip()
    if not s:
        raise ValueError("Empty planner output")

    if s.startswith("{") or s.startswith("["):
        try:
            return json.loads(s)
        except Exception:
            pass

    if ":" not in s:
        if s.lower() == "skip":
            return {"skip": True}
        raise ValueError("Expected 'get:...' or 'search:...' or 'skip'")

    verb, payload = s.split(":", 1)
    verb = verb.strip().lower()
    payload = payload.strip()

    if verb == "get":
        if payload.startswith("[") and payload.endswith("]"):
            arr = json.loads(payload)
            if not isinstance(arr, list):
                raise ValueError("get expects a JSON array of IDs")
            ids: List[str] = []
            for x in arr:
                if not isinstance(x, str):
                    raise ValueError("get array must contain only strings")
                if not _is_valid_pci_id(x.strip()):
                    raise ValueError(f"Invalid PCI ID in array: {x}")
                ids.append(x.strip())
            ids = _dedupe(ids)[:MAX_IDS]
            if not ids:
                raise ValueError("get expects at least one ID")
            return [{"tool_name": "get", "tool_input": {"ids": ids}}]

        # CSV of quoted strings: "10.6","10.5"
        if '","' in payload:
            parts = [p.strip() for p in payload.split(",")]
            ids = []
            for part in parts:
                if not (part.startswith('"') and part.endswith('"') and len(part) >= 2):
                    raise ValueError("get CSV expects only quoted strings")
                sid = part[1:-1].strip()
                if not _is_valid_pci_id(sid):
                    raise ValueError(f"Invalid PCI ID: {sid}")
                ids.append(sid)
            ids = _dedupe(ids)[:MAX_IDS]
            return [{"tool_name": "get", "tool_input": {"ids": ids}}]

        # Tolerant: handles "10.6" "10.5", single-quoted CSV, bare IDs, commas, etc.
        loose_ids = _extract_ids_loose(payload)
        if loose_ids:
            if len(loose_ids) == 1:
                return [{"tool_name": "get", "tool_input": {"id": loose_ids[0]}}]
            return [{"tool_name": "get", "tool_input": {"ids": loose_ids}}]

        raise ValueError(
            'Invalid get payload. Use get:[...] or get:"id" or get:"id1","id2" or tolerant forms like get:"10.5" "10.6"'
        )

    if verb == "search":
        if payload.startswith('"') and payload.endswith('"') and len(payload) >= 2:
            query = payload[1:-1].strip()
            if not query:
                raise ValueError("search expects a non-empty quoted string")
            return [{"tool_name": "search", "tool_input": {"q": query}}]
        # tolerant fallback
        q = payload.strip().strip('"')
        if q:
            return [{"tool_name": "search", "tool_input": {"q": q}}]
        raise ValueError('search expects a query, e.g., search:"topic"')

    raise ValueError(f"Unknown verb: {verb}")

def extract_tool_call(text: str):
    return _parse_compact(text)

def normalize_actions(parsed):
    if isinstance(parsed, dict) and parsed.get("skip") is True:
        return [], None
    if isinstance(parsed, list):
        return parsed, None
    raise ValueError("Unrecognized tool call format (expected compact actions list or skip).")
