from pathlib import Path


def format_prompt(
    user_input: str,
    context: str,
    tool_help: str = "",
    template_type: str = "main",
    tool_result: str = "",
) -> str:
    if template_type == "followup":
        template_path = Path("agent/followup_template.txt")
        template = template_path.read_text(encoding="utf-8")
        return template.replace("{{ tool_result }}", tool_result).replace(
            "{{ user_input }}", user_input
        )

    template_path = Path("agent/prompt_template.txt")
    template = template_path.read_text(encoding="utf-8")
    return (
        template.replace("{{ user_input }}", user_input)
        .replace("{{ context }}", context)
        .replace("{{ tool_help }}", tool_help)
    )
