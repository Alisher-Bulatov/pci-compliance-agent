# mcp_server/pipeline.py

import json
from typing import Any, Dict, List, Sequence, Union

from retrieval.retriever import PCIDocumentRetriever
from tools import get_tool_overview

from agent.llm_wrapper import query_llm
from agent.prompt_formatter import format_prompt
from agent.tool_call_parser import extract_tool_call, normalize_actions
from mcp_server.tool_dispatcher import handle_tool_call

retriever = PCIDocumentRetriever()

# Safety limits so the follow-up prompt can't explode
MAX_ACTIONS = 6
MAX_PER_OBS_CHARS = 6000
MAX_TOTAL_OBS_CHARS = 24000


def _truncate_for_prompt(s: str, limit: int) -> str:
    if s is None:
        return ""
    if len(s) <= limit:
        return s
    return s[: limit - 20] + "... [truncated]"


def _normalize_context_chunks(chunks: Sequence[Union[str, Dict[str, Any]]]) -> str:
    """Convert retriever output (dicts/strings) to a single context string."""
    out: List[str] = []
    for ch in chunks:
        if isinstance(ch, str):
            out.append(ch)
        elif isinstance(ch, dict):
            # Prefer common keys
            text = ch.get("text") or ch.get("content") or ch.get("body")
            if isinstance(text, str) and text.strip():
                out.append(text)
            else:
                # Fallback: compact JSON of a few keys for traceability
                slim = {k: ch[k] for k in ("id", "req_id", "title", "tags") if k in ch}
                out.append(json.dumps(slim, ensure_ascii=False))
        else:
            out.append(str(ch))
    return "\n\n".join(out)


def _extract_top_id_from_observations(observations: List[Dict[str, Any]]) -> str | None:
    """
    Heuristic: grab the first requirement ID from the most recent observation.
    Supports shapes like:
      {"result":[{"id":"1.3", ...}, ...]} or {"result":{"id":"1.3", ...}}
    """
    if not observations:
        return None

    last = observations[-1].get("raw_result")
    data = last
    if isinstance(last, str):
        try:
            data = json.loads(last)
        except Exception:
            data = last

    if isinstance(data, dict):
        res = data.get("result")
        if isinstance(res, list) and res:
            first = res[0]
            if isinstance(first, dict) and "id" in first and isinstance(first["id"], str):
                return first["id"]
        if isinstance(res, dict) and "id" in res and isinstance(res["id"], str):
            return res["id"]

    return None


def _resolve_action_inputs(action: Dict[str, Any], observations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Replace simple placeholders like '<top ID from previous step>' in tool_input
    using the most recent observation. Case-insensitive.
    """
    resolved = dict(action)
    ti = dict(resolved.get("tool_input", {}))

    if not ti:
        resolved["tool_input"] = ti
        return resolved

    # placeholders in lowercase for case-insensitive matching
    placeholders = {
        "<top id>",
        "<top-id>",
        "<top requirement id>",
        "<top requirement>",
        "<top id from previous step>",
    }

    def _needs_replacement(val: Any) -> bool:
        return isinstance(val, str) and any(ph in val.lower() for ph in placeholders)

    if any(_needs_replacement(v) for v in ti.values()):
        top_id = _extract_top_id_from_observations(observations)
        if top_id:
            for k, v in list(ti.items()):
                if _needs_replacement(v):
                    ti[k] = top_id

    resolved["tool_input"] = ti
    return resolved


async def run_full_pipeline(message: str):
    # 1) Retrieve context
    try:
        context_chunks = retriever.retrieve(message, k=3)
    except (RuntimeError, ValueError, OSError) as e:
        yield {"type": "error", "stage": "retrieval", "message": str(e)}
        context_chunks = []

    context_str = _normalize_context_chunks(context_chunks) if context_chunks else ""
    tool_help = get_tool_overview()

    # 2) Get plan from LLM (streaming while buffering)
    yield {"type": "stage", "label": "Planning tool usage..."}
    try:
        prompt = format_prompt(
            user_input=message,
            context=context_str,
            tool_help=tool_help,
            template_type="main",
        )
        plan_text = ""
        token_stream = await query_llm(prompt, stream=True)

        # stream the plan as it's typed
        yield {"type": "token", "text": "\n[PLAN] "}
        async for tok in token_stream:
            plan_text += tok
            yield {"type": "token", "text": tok}
        yield {"type": "token", "text": "\n"}
    except Exception as e:
        yield {"type": "error", "stage": "llm_plan", "message": str(e)}
        return

    # 3) Parse plan → actions or final answer
    try:
        parsed = extract_tool_call(plan_text)
        actions, final_answer = normalize_actions(parsed)
    except Exception as e:
        yield {
            "type": "error",
            "stage": "parse_plan",
            "message": f"Could not parse tool plan: {e}",
        }
        return

    if final_answer is not None:
        # Short-circuit: model already provided the final answer
        yield {"type": "stage", "label": "Producing final answer..."}
        yield {"type": "token", "text": final_answer}
        return

    # 4) Execute actions sequentially
    if actions and len(actions) > MAX_ACTIONS:
        actions = actions[:MAX_ACTIONS]
        yield {
            "type": "info",
            "message": f"Action list truncated to {MAX_ACTIONS} steps for safety.",
        }

    observations: List[Dict[str, Any]] = []
    total_chars = 0

    for idx, action in enumerate(actions, 1):
        # Resolve placeholders based on previous observations
        action = _resolve_action_inputs(action, observations)

        tool_name = action.get("tool_name")
        tool_input = action.get("tool_input", {})

        if not tool_name or not isinstance(tool_input, dict):
            yield {
                "type": "error",
                "stage": "validate_action",
                "message": f"Invalid action format at step {idx}: {action}",
            }
            continue

        yield {
            "type": "stage",
            "label": f"Running {tool_name} ({idx}/{len(actions)})",
        }

        try:
            result = await handle_tool_call(tool_name, tool_input)
        except Exception as e:
            yield {
                "type": "error",
                "stage": "tool_execution",
                "message": f"{tool_name} failed: {e}",
            }
            result = {"error": str(e)}

        # Stream tool output as regular tokens so the UI shows it like LLM text
        try:
            pretty = json.dumps(result, ensure_ascii=False, indent=2)
        except Exception:
            pretty = str(result)

        header = f"\n[TOOL {tool_name}] output:\n"
        for chunk in (header, pretty, "\n"):
            yield {"type": "token", "text": chunk}

        # Keep both raw and truncated strings for follow-up + placeholder resolution
        try:
            raw_json_str = json.dumps(result, ensure_ascii=False)
        except Exception:
            raw_json_str = str(result)

        result_str = _truncate_for_prompt(raw_json_str, MAX_PER_OBS_CHARS)
        total_chars += len(result_str)
        if total_chars > MAX_TOTAL_OBS_CHARS:
            result_str = "[omitted due to total size limit]"

        observations.append(
            {
                "tool": tool_name,
                "input": tool_input,
                "result": result_str,   # truncated string for follow-up
                "raw_result": result,   # raw object used by placeholder resolver
            }
        )

        if total_chars > MAX_TOTAL_OBS_CHARS:
            yield {
                "type": "info",
                "message": "Further observations omitted due to size limits.",
            }
            break

    # 5) Follow-up reasoning using all observations
    yield {"type": "stage", "label": "Reasoning based on tool results..."}
    tool_result_str = json.dumps(observations, ensure_ascii=False)

    followup_prompt = format_prompt(
        user_input=message,
        context="",          # keep follow-up focused on observations
        tool_help="",        # not needed now
        template_type="followup",
        tool_result=tool_result_str,
    )

    try:
        token_stream = await query_llm(followup_prompt, stream=True)
        async for token in token_stream:
            yield {"type": "token", "text": token}
    except (ConnectionError, TimeoutError, RuntimeError) as e:
        yield {"type": "error", "stage": "llm_followup", "message": str(e)}
