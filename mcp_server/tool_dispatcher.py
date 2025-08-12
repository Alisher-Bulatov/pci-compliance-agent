# mcp_server/tool_dispatcher.py

from __future__ import annotations

import asyncio
import importlib
import inspect
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)
tool_router = APIRouter()

# ---------------- Models ----------------

class ToolCall(BaseModel):
    tool_name: str
    tool_input: Dict[str, Any] = {}

# ---------------- Helpers ----------------

def _import_tool_module(tool_name: str):
    try:
        return importlib.import_module(f"tools.{tool_name}")
    except ModuleNotFoundError as e:
        raise ModuleNotFoundError(f"Tool '{tool_name}' not found (tried tools.{tool_name})") from e

def _error_response(stage: str, message: str, tool_name: str,
                    details: Optional[Any] = None) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "status": "error",
        "tool_name": tool_name,
        "stage": stage,
        "message": message,
    }
    if details is not None:
        out["details"] = details
    return out

def _serialize_output(obj: Any) -> Dict[str, Any]:
    if obj is None:
        return {"status": "success", "result": None}
    if isinstance(obj, BaseModel):
        d = obj.model_dump() if hasattr(obj, "model_dump") else obj.dict()
        return d if "status" in d else {"status": "success", **d}
    if isinstance(obj, dict):
        return obj if "status" in obj else {"status": "success", **obj}
    return {"status": "success", "result": obj}

# ---------------- Dispatcher ----------------

async def handle_tool_call_async(tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    try:
        module = _import_tool_module(tool_name)
    except ModuleNotFoundError as e:
        return _error_response("import", str(e), tool_name)

    run_fn = getattr(module, "run", None)
    if run_fn is None or not callable(run_fn):
        return _error_response("dispatch", f"Tool '{tool_name}' has no callable 'run'", tool_name)

    try:
        result_obj = run_fn(tool_input or {})
        if inspect.isawaitable(result_obj):
            result_obj = await result_obj
    except ValidationError as ve:
        return _error_response("validation", "Input validation failed", tool_name, details=ve.errors())
    except (AttributeError, TypeError, ValueError) as known_error:
        return _error_response("runtime", str(known_error), tool_name)
    except Exception as e:
        logger.exception("Unhandled error running tool '%s'", tool_name)
        return _error_response("runtime", f"Unhandled error: {e}", tool_name)

    return _serialize_output(result_obj)

def handle_tool_call(tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Synchronous wrapper — ONLY safe when no event loop is running.
    If a loop exists, raise a clear guidance error (so devs switch to await handle_tool_call_async).
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        import anyio
        return anyio.run(handle_tool_call_async, tool_name, tool_input or {})
    else:
        raise RuntimeError(
            "handle_tool_call() called from an async context. "
            "Use: `await handle_tool_call_async(...)`"
        )

# ---------------- HTTP route ----------------

@tool_router.post("/tools/call")
async def call_tool(tc: ToolCall) -> Dict[str, Any]:
    return await handle_tool_call_async(tc.tool_name, tc.tool_input)
