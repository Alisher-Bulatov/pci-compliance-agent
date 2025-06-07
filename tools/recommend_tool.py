def main(suggested_tool, reason=None, query="", requirement_id=None):
    print(f"ℹ️ Recommending tool: {suggested_tool} | Reason: {reason}")

    if suggested_tool == "search_by_topic":
        return {"tool_name": "search_by_topic", "tool_input": {"query": query}}

    if suggested_tool == "get_requirement_text":
        return {
            "tool_name": "get_requirement_text",
            "tool_input": {"requirement_id": requirement_id},
        }

    return {"result": f"⚠️ Cannot delegate to tool: {suggested_tool}"}
