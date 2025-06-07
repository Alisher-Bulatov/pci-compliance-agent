from typing import Literal
from pydantic import BaseModel
from agent.tool_schema import BaseToolOutputSchema


class InputSchema(BaseModel):
    query: str


class OutputSchema(BaseToolOutputSchema):
    tool_name: Literal["recommend_tool"]
    result: dict


def main(input_data: InputSchema) -> OutputSchema:
    q = input_data.query.lower()

    if any(
        keyword in q for keyword in ["compare", "difference", "diff", "between", "vs"]
    ):
        tool = "compare_requirements"
        reason = "Input suggests comparing multiple requirements."
    elif any(x in q for x in ["say", "state", "exact", "wording", "what does", "3."]):
        tool = "get_requirement_text"
        reason = "Input requests exact text of a specific requirement."
    else:
        tool = "search_by_topic"
        reason = "Input is general or exploratory in nature."

    return OutputSchema(
        tool_name="recommend_tool",
        result={
            "suggested_tool": tool,
            "reason": reason,
            "query": input_data.query,
        },
    )
