"""Compare the differences between two or more PCI DSS requirements."""

from typing import List, Literal

import requests
from pydantic import BaseModel

from agent.models.requirement import RequirementEntry, RequirementOutput


class InputSchema(BaseModel):
    requirement_ids: List[str]


class OutputSchema(RequirementOutput):
    tool_name: Literal["compare_requirements"]


def main(input_data: InputSchema) -> OutputSchema:
    """Fetches and compares the requirement texts based on given IDs."""
    results: List[RequirementEntry] = []

    for req_id in input_data.requirement_ids:
        try:
            payload = {
                "tool_name": "get_requirement_text",
                "tool_input": {"requirement_id": req_id},
            }
            response = requests.post(
                "http://localhost:8000/tool_call",
                json=payload,
                timeout=10,
            )
            response.raise_for_status()
            outer = response.json().get("result", {})

            entry = RequirementEntry(
                id=outer.get("id", req_id),
                text=outer.get("text", "Unavailable"),
                tags=outer.get("tags", []),
            )
            results.append(entry)

        except requests.RequestException as e:
            results.append(
                RequirementEntry(
                    id=req_id,
                    text=f"❌ Failed to fetch: {e}",
                    tags=[],
                )
            )

    return OutputSchema(tool_name="compare_requirements", result=results)
