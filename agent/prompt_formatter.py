from pathlib import Path

TEMPLATES = {
    "default": Path("agent/prompt_template.txt"),
    "followup": Path("agent/followup_template.txt"),
}

def format_prompt(user_input: str, context: str, type: str = "default", **kwargs) -> str:
    path = TEMPLATES.get(type, TEMPLATES["default"])
    with open(path, "r", encoding="utf-8") as f:
        template = f.read()
    return template.format_map({
        "user_input": user_input,
        "context": context,
        **kwargs
    })
