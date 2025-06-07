import importlib
import logging
from typing import Any, Dict

from fastapi import APIRouter
from pydantic import BaseModel, ValidationError

tool_router = APIRouter()
logger = logging.getLogger(__name__)


class ToolCall(BaseModel):
    tool_name: str
    tool_input: Dict[str, Any]


def error_response(stage: str, message: str, tool_name: str, **extra) -> Dict[str, Any]:
    return {
        "status": "error",
        "stage": stage,
        "message": message,
        "tool_name": tool_name,
        **extra,
    }


def handle_tool_call(tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    try:
        tool_module = importlib.import_module(f"tools.{tool_name}")
        InputSchema = getattr(tool_module, "InputSchema", None)
        OutputSchema = getattr(tool_module, "OutputSchema", None)
        main_func = getattr(tool_module, "main", None)

        if not callable(main_func):
            raise TypeError("Tool 'main' is not callable")

        if InputSchema is None or OutputSchema is None:
            raise AttributeError("Tool must define both InputSchema and OutputSchema")

        input_obj = InputSchema(**tool_input)
        result_obj = main_func(input_obj)

        if not isinstance(result_obj, OutputSchema):
            raise TypeError("Tool did not return OutputSchema instance")

        return {
            "status": "success",
            "tool_name": tool_name,
            "result": result_obj.serialized_result(),
        }

    except ModuleNotFoundError:
        return error_response("import", f"Tool '{tool_name}' not found", tool_name)

    except ValidationError as ve:
        return error_response(
            "validation", "Input validation failed", tool_name, details=ve.errors()
        )

    except (AttributeError, TypeError, ValueError) as known_error:
        return error_response("execution", str(known_error), tool_name)

    except Exception as e:
        logger.exception("Tool execution failed for '%s'", tool_name)
        raise RuntimeError(f"Unhandled exception in tool '{tool_name}': {e}") from e


@tool_router.post("/tool_call")
def tool_call_handler(call: ToolCall) -> Dict[str, Any]:
    return handle_tool_call(call.tool_name, call.tool_input)
