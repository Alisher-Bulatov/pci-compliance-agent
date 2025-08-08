import json

def extract_tool_call(text: str) -> dict:
    """
    Extracts the first complete JSON object/array from the text, or detects 'skip'.
    Returns:
      - {"skip": True} if the model output is exactly 'skip' (case-insensitive, ignoring whitespace)
      - Parsed JSON object otherwise
    """
    # 1) Direct skip detection
    if text.strip().lower() == "skip":
        return {"skip": True}

    # 2) JSON extraction
    start = text.find("{")
    start_list = text.find("[")
    if start_list != -1 and (start_list < start or start == -1):
        start = start_list
    if start == -1:
        raise ValueError("Could not extract TOOL_CALL/TOOL_PLAN from LLM output.")

    depth = 0
    for idx in range(start, len(text)):
        char = text[idx]
        if char in "{[":
            depth += 1
        elif char in "}]":
            depth -= 1
            if depth == 0:
                candidate = text[start: idx + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError as e:
                    raise ValueError(
                        "Could not parse JSON tool plan from LLM output."
                    ) from e
    raise ValueError("Could not extract TOOL_CALL/TOOL_PLAN from LLM output.")


def normalize_actions(parsed_json):
    """
    Returns (actions_list, final_answer_or_None).
    Supports:
      - {"skip": True}  → skip mode, no actions
      - single dict {tool_name, tool_input}
      - list of {tool_name, tool_input}
      - dict with 'actions': [...]
    """
    # Handle skip case
    if isinstance(parsed_json, dict) and parsed_json.get("skip") is True:
        return [], None  # Skip = no actions, no final answer

    if isinstance(parsed_json, list):
        return parsed_json, None

    if isinstance(parsed_json, dict):
        if "actions" in parsed_json and isinstance(parsed_json["actions"], list):
            return parsed_json["actions"], None

        if "tool_name" in parsed_json and "tool_input" in parsed_json:
            return [parsed_json], None

    raise ValueError("Unrecognized tool call format.")
