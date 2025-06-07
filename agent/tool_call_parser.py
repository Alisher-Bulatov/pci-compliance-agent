import json
import re


def extract_tool_call(text: str) -> dict:
    try:
        match = re.search(r"{.*}", text, re.DOTALL)
        return json.loads(match.group(0))
    except Exception as e:
        raise ValueError("Could not extract TOOL_CALL from LLM output.") from e
