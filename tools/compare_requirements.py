from typing import List, Literal
from pydantic import BaseModel
from agent.models.requirement import RequirementEntry, RequirementOutput

import httpx
import os
import asyncio


class InputSchema(BaseModel):
    requirement_ids: List[str]


class OutputSchema(RequirementOutput):
    tool_name: Literal["compare_requirements"]


async def fetch_requirement(req_id: str) -> RequirementEntry:
    try:
        payload = {
            "tool_name": "get_requirement_text",
            "tool_input": {"requirement_id": req_id},
        }
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{os.getenv('MCP_API_URL', 'http://localhost:8000')}/tool_call",
                json=payload,
            )
            response.raise_for_status()
            outer = response.json().get("result", {})

        return RequirementEntry(
            id=outer.get("id", req_id),
            text=outer.get("text", "Unavailable"),
            tags=outer.get("tags", []),
        )
    except httpx.RequestError as e:
        return RequirementEntry(
            id=req_id,
            text=f"❌ Failed to fetch: {e}",
            tags=[],
        )


async def main(input_data: InputSchema) -> OutputSchema:
    tasks = [fetch_requirement(req_id) for req_id in input_data.requirement_ids]
    results = await asyncio.gather(*tasks)
    return OutputSchema(tool_name="compare_requirements", result=results)
