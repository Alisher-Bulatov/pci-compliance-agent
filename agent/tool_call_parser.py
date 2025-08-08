import json

def extract_tool_call(text: str) -> dict:
    """Extract the first complete JSON object or array from text."""
    start = text.find("{")
    start_list = text.find("[")
    if start_list != -1 and (start_list < start or start == -1):
        start = start_list
    if start == -1:
        raise ValueError("Could not extract TOOL_CALL/TOOL_PLAN from LLM output.")

    depth = 0
    in_list = text[start] == "["
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
      - single dict {tool_name, tool_input}
      - list of {tool_name, tool_input}
      - dict with 'actions': [...]
      - dict with 'answer': <string>  (FINAL_ANSWER)
    """
    if isinstance(parsed_json, list):
        return parsed_json, None

    if isinstance(parsed_json, dict):
        if "answer" in parsed_json:
            return [], parsed_json["answer"]

        if "actions" in parsed_json and isinstance(parsed_json["actions"], list):
            return parsed_json["actions"], None

        if "tool_name" in parsed_json and "tool_input" in parsed_json:
            return [parsed_json], None

    raise ValueError("Unrecognized tool call format.")
