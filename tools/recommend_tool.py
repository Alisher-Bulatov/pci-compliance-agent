# tools/recommend_tool.py

def run(tool_input):
    suggested_tool = tool_input["suggested_tool"]
    reason = tool_input.get("reason", "No reason provided.")
    query = tool_input.get("query", "")

    print(f"ℹ️ Recommending tool: {suggested_tool} | Reason: {reason}")

    if suggested_tool == "search_by_topic":
        return {
            "tool_name": "search_by_topic",
            "tool_input": {"query": query}
        }

    if suggested_tool == "get_requirement_text":
        return {
            "tool_name": "get_requirement_text",
            "tool_input": {"requirement_id": tool_input.get("requirement_id", "")}
        }

    # fallback passthrough if unsupported
    return {"result": f"⚠️ Cannot delegate to tool: {suggested_tool}"}
