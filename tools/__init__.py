import importlib
import inspect
import pkgutil
from typing import Dict
from pydantic import BaseModel

TOOL_REGISTRY: Dict[str, Dict[str, object]] = {}


def load_tools():
    for _, module_name, _ in pkgutil.iter_modules(__path__):
        if module_name == "__init__":
            continue

        module = importlib.import_module(f"tools.{module_name}")

        input_schema = getattr(module, "InputSchema", None)
        description = getattr(module, "__doc__", "").strip().split("\n")[0]

        if (
            input_schema
            and inspect.isclass(input_schema)
            and issubclass(input_schema, BaseModel)
        ):
            TOOL_REGISTRY[module_name] = {
                "description": description or f"{module_name} tool.",
                "input_schema": input_schema,
            }


# Call once at import
load_tools()


def get_tool_overview() -> str:
    lines = []
    for tool_name, meta in TOOL_REGISTRY.items():
        lines.append(f"🔧 **{tool_name}**: {meta['description']}")
        fields = meta["input_schema"].model_fields
        for field_name, field in fields.items():
            f_type = field.annotation.__name__
            lines.append(f"  • `{field_name}`: {f_type}")
        lines.append("")
    return "\n".join(lines)
