import importlib
import inspect
import pkgutil
from typing import Dict
import logging
from pydantic import BaseModel


logger = logging.getLogger(__name__)


TOOL_REGISTRY: Dict[str, Dict[str, object]] = {}


def load_tools():
    for _, module_name, _ in pkgutil.iter_modules(__path__):
        if module_name == "__init__":
            continue

        try:
            module = importlib.import_module(f"tools.{module_name}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to import tools.{module_name}: {e}")
            continue

        input_schema = getattr(module, "InputSchema", None)

        raw_doc = getattr(module, "__doc__", None)
        description = (
            raw_doc.strip().split("\n")[0]
            if isinstance(raw_doc, str) and raw_doc.strip()
            else f"{module_name} tool"
        )

        if (
            input_schema
            and inspect.isclass(input_schema)
            and issubclass(input_schema, BaseModel)
        ):
            TOOL_REGISTRY[module_name] = {
                "description": description,
                "input_schema": input_schema,
            }


# Load at module import time
load_tools()


def get_tool_overview() -> str:
    lines = []
    for tool_name, meta in TOOL_REGISTRY.items():
        lines.append(f"🔧 **{tool_name}**: {meta['description']}")
        fields = meta["input_schema"].model_fields
        for field_name, field in fields.items():
            f_type = (
                field.annotation.__name__
                if hasattr(field.annotation, "__name__")
                else str(field.annotation)
            )
            lines.append(f"  • `{field_name}`: {f_type}")
        lines.append("")
    return "\n".join(lines)
