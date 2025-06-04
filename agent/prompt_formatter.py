def format_prompt(user_input: str, context: str) -> str:
    with open("agent/prompt_template.txt", "r", encoding="utf-8") as f:
        template = f.read()
    return template.format(user_input=user_input, context=context)
