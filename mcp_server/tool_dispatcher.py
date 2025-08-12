# mcp_server/tool_dispatcher.py

import importlib
import inspect
import logging
from typing import Any, Dict

import anyio
from fastapi import APIRouter
from pydantic import BaseModel, ValidationError

tool_router = APIRouter()
logger = logging.getLogger(__name__)


class ToolCall(BaseModel):
    tool_name: str
    tool_input: Dict[str, Any]


def _serialize_output(obj: Any) -> Dict[str, Any]:
    """
    Normalize a tool's return value to a plain dict for transport.
    Supports Pydantic v1/v2 models as well as raw dicts.
    """
    if obj is None:
        return {"status": "error", "tool_name": "unknown", "result": [], "meta": {"error": "tool returned None"}}

    # Pydantic v2
    if hasattr(obj, "model_dump") and callable(obj.model_dump):
        return obj.model_dump()

    # Pydantic v1
    if hasattr(obj, "dict") and callable(obj.dict):
        return obj.dict()

    if isinstance(obj, dict):
        return obj

    # Fallback best-effort
    try:
        return dict(obj)
    except Exception:
        return {"status": "error", "tool_name": "unknown", "result": [], "meta": {"error": f"unserializable: {type(obj)}"}}


def _error_response(kind: str, message: str, tool_name: str, details: Any | None = None) -> Dict[str, Any]:
    meta = {"kind": kind, "error": message}
    if details is not None:
        meta["details"] = details
    return {
        "status": "error",
        "tool_name": tool_name,
        "result": [],
        "meta": meta,
    }


async def handle_tool_call_async(tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Async entrypoint (use this from FastAPI routes).
    Dynamically imports tools.<tool_name> and calls its `run(payload)` function.
    """
    try:
        module = importlib.import_module(f"tools.{tool_name}")
    except ModuleNotFoundError:
        return _error_response("import", f"Tool '{tool_name}' not found", tool_name)

    run_fn = getattr(module, "run", None)
    if run_fn is None or not callable(run_fn):
        return _error_response("dispatch", f"Tool '{tool_name}' has no callable 'run'", tool_name)

    # Run the tool (most tools are sync functions; if it returns a pydantic model, serialize it)
    try:
        result_obj = run_fn(tool_input)
    except ValidationError as ve:
        return _error_response("validation", "Input validation failed", tool_name, details=ve.errors())
    except (AttributeError, TypeError, ValueError) as known_error:
        return _error_response("runtime", str(known_error), tool_name)
    except Exception as e:  # unexpected
        logger.exception("Unexpected error running tool '%s'", tool_name)
        return _error_response("runtime", f"Unhandled error: {e}", tool_name)

    return _serialize_output(result_obj)


def handle_tool_call(tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sync wrapper for code paths that aren't async (e.g., your pipeline).
    This avoids 'coroutine was never awaited' errors without refactoring callers.
    """
    return anyio.run(handle_tool_call_async, tool_name, tool_input)


@tool_router.post("/tools/call")
async def call_tool(tc: ToolCall) -> Dict[str, Any]:
    """
    FastAPI route to invoke a tool. Returns normalized dict output.
    """
    return await handle_tool_call_async(tc.tool_name, tc.tool_input)
