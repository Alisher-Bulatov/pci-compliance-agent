from fastapi import APIRouter
from pydantic import BaseModel
import importlib

tool_router = APIRouter()

class ToolCall(BaseModel):
    tool_name: str
    tool_input: dict

# Internal dispatcher for programmatic (non-HTTP) use
def handle_tool_call(tool_name: str, tool_input: dict):
    try:
        tool_module = importlib.import_module(f"tools.{tool_name}")
        if hasattr(tool_module, "main"):
            return tool_module.main(**tool_input)
        else:
            return {"error": f"Tool '{tool_name}' found but missing `main()` function"}
    except ModuleNotFoundError:
        return {"error": f"Tool '{tool_name}' not found"}
    except Exception as e:
        return {"error": str(e), "tool_name": tool_name}


# HTTP POST route
@tool_router.post("/tool_call")
def tool_call_handler(call: ToolCall):
    return {"result": handle_tool_call(call.tool_name, call.tool_input)}
