import json


def extract_tool_call(text: str) -> dict:
    """Extract the first complete JSON object from ``text``.

    We previously relied on a greedy regex which broke when multiple JSON
    blocks appeared in the LLM output. A naive non-greedy regex fails with
    nested braces. Instead we scan for the first ``{`` and track opening and
    closing braces until they balance, ensuring nested objects are handled
    correctly.
    """

    # Locate the first opening brace. If none exists, there's nothing to parse.
    start = text.find("{")
    if start == -1:
        raise ValueError("Could not extract TOOL_CALL from LLM output.")

    depth = 0
    for idx in range(start, len(text)):
        char = text[idx]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start : idx + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError as e:
                    raise ValueError(
                        "Could not extract TOOL_CALL from LLM output."
                    ) from e

    raise ValueError("Could not extract TOOL_CALL from LLM output.")
