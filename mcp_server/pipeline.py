from retrieval.retriever import PCIDocumentRetriever
from tools import get_tool_overview

from agent.llm_wrapper import query_llm
from agent.prompt_formatter import format_prompt
from agent.tool_call_parser import extract_tool_call
from mcp_server.tool_dispatcher import handle_tool_call

retriever = PCIDocumentRetriever()


async def run_full_pipeline(message: str):
    yield {"type": "stage", "label": "Retrieving related requirements"}
    try:
        context_chunks = retriever.retrieve(message, k=3)
    except (RuntimeError, ValueError, OSError) as e:
        yield {"type": "error", "stage": "retrieval", "message": str(e)}
        return

    context = "\n".join(
        f"Requirement {c['id']}: {c['text']} [tags: {', '.join(c.get('tags', []))}]"
        for c in context_chunks
    )

    tool_help = get_tool_overview()
    prompt = format_prompt(
        user_input=message, context=context, tool_help=tool_help, template_type="main"
    )

    yield {"type": "stage", "label": "Thinking..."}
    buffered = ""
    try:
        token_stream = await query_llm(prompt, stream=True)
        async for token in token_stream:
            yield {"type": "token", "text": token}
            buffered += token
    except (ConnectionError, TimeoutError, RuntimeError) as e:
        yield {"type": "error", "stage": "llm_initial", "message": str(e)}
        return

    try:
        tool_call = extract_tool_call(buffered)
    except ValueError:
        tool_call = None

    if not tool_call:
        yield {
            "type": "info",
            "message": "✅ No tool call detected. Response complete.",
        }
        return

    yield {"type": "stage", "label": "Tool call detected, executing..."}

    try:
        tool_result = await handle_tool_call(
            tool_call["tool_name"], tool_call["tool_input"]
        )
        yield {"type": "tool_result", "text": tool_result}
    except (KeyError, TypeError, ValueError) as e:
        yield {"type": "error", "stage": "tool", "message": str(e)}
        return

    flattened_result = tool_result.get("result", tool_result)
    if isinstance(flattened_result, list):
        tool_result_str = "\n".join(
            f"Requirement {r['id']}: {r['text']} [tags: {', '.join(r.get('tags', []))}]"
            for r in flattened_result
        )
    else:
        tool_result_str = str(flattened_result)

    followup_prompt = format_prompt(
        user_input=message,
        context="",
        tool_help="",
        template_type="followup",
        tool_result=tool_result_str,
    )

    yield {"type": "stage", "label": "Reasoning based on tool result..."}
    try:
        token_stream = await query_llm(followup_prompt, stream=True)
        async for token in token_stream:
            yield {"type": "token", "text": token}
    except (ConnectionError, TimeoutError, RuntimeError) as e:
        yield {"type": "error", "stage": "llm_followup", "message": str(e)}
