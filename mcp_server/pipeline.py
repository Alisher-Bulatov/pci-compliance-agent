from agent.llm_wrapper import query_llm
from agent.prompt_formatter import format_prompt
from agent.tool_call_parser import extract_tool_call
from mcp_server.tool_dispatcher import handle_tool_call
from retrieval.retriever import PCIDocumentRetriever

retriever = PCIDocumentRetriever()

# Legacy: plain-text streaming
def run_full_pipeline(message: str):
    yield "\n🔍 Retrieving related requirements...\n\n"
    try:
        context_chunks = retriever.retrieve(message, k=3)
    except Exception as e:
        yield f"\n❌ Retrieval failed: {e}\n\n"
        return

    context = "\n".join(
        f"Requirement {c['id']}: {c['text']} [tags: {', '.join(c.get('tags', []))}]"
        for c in context_chunks
    )

    prompt = format_prompt(message, context)

    yield "\n🧠 Thinking...\n\n>>> "
    buffered = ""
    try:
        for token in query_llm(prompt, stream=True):
            yield token
            buffered += token
    except Exception as e:
        yield f"\n❌ LLM query failed: {e}\n\n"
        return

    try:
        tool_call = extract_tool_call(buffered)
    except Exception:
        tool_call = None

    if not tool_call:
        yield "\n\n✅ No tool call detected. Response complete.\n\n"
        return

    yield "\n\n🛠 Tool call detected, executing...\n\n"

    try:
        tool_result = handle_tool_call(tool_call["tool_name"], tool_call["tool_input"])
        tool_result_str = (
            "\n".join(
                f"Requirement {r['id']}: {r['text']} [tags: {', '.join(r.get('tags', []))}]"
                for r in tool_result
            )
            if isinstance(tool_result, list)
            else str(tool_result)
        )
        yield f"\n→ Tool Result:\n\n{tool_result_str}\n"
    except Exception as e:
        yield f"\n❌ Tool execution failed: {e}\n\n"
        return

    followup_prompt = format_prompt(
        user_input=message,
        context="",
        type="followup",
        tool_result=tool_result_str,
    )

    yield "\n🧠 Reasoning based on tool result...\n\n>>> "
    try:
        for token in query_llm(followup_prompt, stream=True):
            yield token
    except Exception as e:
        yield f"\n❌ Follow-up reasoning failed: {e}\n\n"

# ✅ New: Structured event-based pipeline
def run_full_pipeline_verbose(message: str):
    yield { "type": "stage", "label": "Retrieving related requirements" }
    try:
        context_chunks = retriever.retrieve(message, k=3)
    except Exception as e:
        yield { "type": "error", "stage": "retrieval", "message": str(e) }
        return

    context = "\n".join(
        f"Requirement {c['id']}: {c['text']} [tags: {', '.join(c.get('tags', []))}]"
        for c in context_chunks
    )

    prompt = format_prompt(message, context)

    yield { "type": "stage", "label": "Thinking..." }
    buffered = ""
    try:
        for token in query_llm(prompt, stream=True):
            yield { "type": "token", "text": token }
            buffered += token
    except Exception as e:
        yield { "type": "error", "stage": "llm_initial", "message": str(e) }
        return

    try:
        tool_call = extract_tool_call(buffered)
    except Exception:
        tool_call = None

    if not tool_call:
        yield { "type": "info", "message": "✅ No tool call detected. Response complete." }
        return

    yield { "type": "stage", "label": "Tool call detected, executing..." }

    try:
        tool_result = handle_tool_call(tool_call["tool_name"], tool_call["tool_input"])
        tool_result_str = (
            "\n".join(
                f"Requirement {r['id']}: {r['text']} [tags: {', '.join(r.get('tags', []))}]"
                for r in tool_result
            )
            if isinstance(tool_result, list)
            else str(tool_result)
        )
        yield { "type": "tool_result", "text": tool_result_str }
    except Exception as e:
        yield { "type": "error", "stage": "tool", "message": str(e) }
        return

    followup_prompt = format_prompt(
        user_input=message,
        context="",
        type="followup",
        tool_result=tool_result_str,
    )

    yield { "type": "stage", "label": "Reasoning based on tool result..." }
    try:
        for token in query_llm(followup_prompt, stream=True):
            yield { "type": "token", "text": token }
    except Exception as e:
        yield { "type": "error", "stage": "llm_followup", "message": str(e) }
