import json

# Hard caps so someone can't make you fetch 10k IDs in one go
MAX_IDS = 50

def _is_valid_pci_id(s: str) -> bool:
    """
    Valid PCI ID rules (no regex):
      - First segment: integer 1..12 (no leading +/-, no decimals)
      - Then 0..3 dot-separated segments
      - Each extra segment is 1..2 digits (00..99), but we keep it simple: 0..99 allowed
      - Examples: 3, 10, 3.2, 3.2.1, 11.5.1.1
      - Non-examples: 13, v4.0.1, 3.x, 0.1, 1.2.3.4.5
    """
    if not s or " " in s:
        return False
    parts = s.split(".")
    if not parts:
        return False

    # First part 1..12
    p0 = parts[0]
    if not p0.isdigit():
        return False
    n0 = int(p0)
    if n0 < 1 or n0 > 12:
        return False

    # Up to 3 more parts, each 1..2 digits (00–99 is tolerated; spec doesn't forbid 00 explicitly)
    tail = parts[1:]
    if len(tail) > 3:
        return False
    for t in tail:
        if not (t.isdigit() and 1 <= len(t) <= 2):
            return False

    return True


def _dedupe_preserve_order(items):
    seen = set()
    out = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def extract_tool_call(text: str):
    """
    Parses compact planner output or 'skip'.

    Accepts exactly one of:
      - "skip" (any case, surrounding whitespace allowed)
      - get:["6.5","1.2.1"]    # batch IDs (JSON array of strings)
      - get:"6.5"              # single ID (quoted string)
      - search:"cryptographic key storage"  # single quoted string

    Returns:
      - {"skip": True}  for skip
      - list of action dicts: [{"tool_name": "...", "tool_input": {...}}]

    Raises:
      - ValueError on any other format.
    """
    if not isinstance(text, str):
        raise ValueError("Planner output must be a string")

    s = text.strip()

    # 1) Direct skip detection
    if s.lower() == "skip":
        return {"skip": True}

    # 2) Compact verb:payload parsing
    if ":" not in s:
        raise ValueError("Planner output missing ':' and is not 'skip'")

    verb, payload = s.split(":", 1)
    verb, payload = verb.strip(), payload.strip()

    if verb == "get":
        # Batch: get:["6.5","1.2.1"]
        if payload.startswith("["):
            try:
                ids = json.loads(payload)
            except Exception as e:
                raise ValueError(f"Invalid JSON array for get: {e}")

            if not isinstance(ids, list) or not all(isinstance(x, str) for x in ids):
                raise ValueError("get expects a JSON array of strings")

            # strip whitespace inside elements, validate, dedupe, cap
            cleaned = []
            for x in ids:
                x2 = x.strip()
                if not x2:
                    raise ValueError("get contains an empty ID")
                if not _is_valid_pci_id(x2):
                    raise ValueError(f"Invalid PCI ID: {x2}")
                cleaned.append(x2)

            cleaned = _dedupe_preserve_order(cleaned)
            if len(cleaned) > MAX_IDS:
                raise ValueError(f"Too many IDs in get (>{MAX_IDS})")

            return [{"tool_name": "get", "tool_input": {"ids": cleaned}}]

        # Single: get:"6.5"
        if payload.startswith('"') and payload.endswith('"') and len(payload) >= 2:
            single_id = payload[1:-1].strip()
            if not single_id:
                raise ValueError("get expects a non-empty ID")
            if not _is_valid_pci_id(single_id):
                raise ValueError(f"Invalid PCI ID: {single_id}")
            return [{"tool_name": "get", "tool_input": {"ids": [single_id]}}]

        raise ValueError('Invalid get payload. Use get:[...] or get:"id"')

    if verb == "search":
        # search:"cryptographic key storage"
        if payload.startswith('"') and payload.endswith('"') and len(payload) >= 2:
            query = payload[1:-1].strip()
            if not query:
                raise ValueError("search expects a non-empty quoted string")
            # Soft sanity: discourage ID-like-only queries. Router should handle this,
            # but this protects you if the planner glitches.
            if _is_valid_pci_id(query):
                # Still allow (your router rule should avoid this anyway), but you can tighten if desired.
                pass
            return [{"tool_name": "search", "tool_input": {"query": query}}]

        raise ValueError('search expects a single quoted string, e.g. search:"topic"')

    raise ValueError(f"Unknown verb: {verb}")


def normalize_actions(parsed):
    """
    Returns (actions_list, final_answer_or_None).

    Supported inputs:
      - {"skip": True}                  → returns ([], None)
      - list of {tool_name, tool_input} → returns (list, None)

    Any other input raises ValueError (no JSON fallback in this mode).
    """
    if isinstance(parsed, dict) and parsed.get("skip") is True:
        return [], None

    if isinstance(parsed, list):
        return parsed, None

    raise ValueError("Unrecognized tool call format (expected compact actions list or skip).")
