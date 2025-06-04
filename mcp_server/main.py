from fastapi import FastAPI
from pydantic import BaseModel
from tools.get_requirement_text import get_requirement_text
from tools.compare_requirements import compare_requirements
from tools.search_by_topic import search_by_topic

app = FastAPI()

class ToolCall(BaseModel):
    tool_name: str
    tool_input: dict

@app.post("/tool_call")
def tool_call_handler(call: ToolCall):
    if call.tool_name == "get_requirement_text":
        req_id = call.tool_input.get("requirement_id", "")
        return {"result": get_requirement_text(req_id)}
    elif call.tool_name == "compare_requirements":
        req_ids = call.tool_input.get("requirement_ids", [])
        return {"result": compare_requirements(req_ids)}
    elif call.tool_name == "search_by_topic":
        query = call.tool_input.get("query", "")
        return {"result": search_by_topic(query)}
    return {"error": "Unknown tool"}
