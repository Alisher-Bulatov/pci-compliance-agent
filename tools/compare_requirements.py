from tools.get_requirement_text import get_requirement_text

def compare_requirements(requirement_ids):
    if not isinstance(requirement_ids, list) or len(requirement_ids) < 2:
        return "Please provide at least two requirement IDs to compare."

    output = []
    for req_id in requirement_ids:
        text = get_requirement_text(req_id)
        output.append(f"Requirement {req_id}:\n{text}\n")

    output.append("Summary:")
    for req_id in requirement_ids:
        output.append(f"- {req_id}: see above for details.")

    return "\n".join(output)
