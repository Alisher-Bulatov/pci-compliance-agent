from fastapi import FastAPI
from pydantic import BaseModel
from tools.get_requirement_text import get_requirement_text

app = FastAPI()

class ToolCall(BaseModel):
    tool_name: str
    tool_input: dict

@app.post("/tool_call")
def tool_call_handler(call: ToolCall):
    if call.tool_name == "get_requirement_text":
        req_id = call.tool_input.get("requirement_id", "")
        return {"result": get_requirement_text(req_id)}
    return {"error": "Unknown tool"}