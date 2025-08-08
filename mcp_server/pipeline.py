# mcp_server/pipeline.py

import json
import re
from typing import Any, Dict, List, Sequence, Union

from tools import get_tool_overview

from agent.llm_wrapper import query_llm
from agent.prompt_formatter import format_prompt
from agent.tool_call_parser import extract_tool_call, normalize_actions
from mcp_server.tool_dispatcher import handle_tool_call

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
    """(Unused in planning now) Convert retriever output (dicts/strings) to a single context string."""
    out: List[str] = []
    for ch in chunks:
        if isinstance(ch, str):
            out.append(ch)
        elif isinstance(ch, dict):
            text = ch.get("text") or ch.get("content") or ch.get("body")
            if isinstance(text, str) and text.strip():
                out.append(text)
            else:
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


def _format_tool_output(tool_name: str, result_obj: Any, tool_input: Dict[str, Any] | None = None) -> str:
    """
    Convert raw tool result to a human-friendly summary string.
    We DO NOT emit raw JSON to the chat.
    """
    try:
        res = result_obj if isinstance(result_obj, dict) else {}
        status = res.get("status")
        payload = res.get("result")

        if tool_name == "search":
            if isinstance(payload, list) and payload:
                lines = []
                for item in payload[:10]:  # cap to 10 items
                    if isinstance(item, dict):
                        rid = (item.get("id") or "").strip()
                        txt = (item.get("text") or "").strip()
                        if txt and len(txt) > 220:
                            txt = txt[:220].rstrip() + "…"
                        if rid and txt:
                            lines.append(f"- {rid}: {txt}")
                        elif rid:
                            lines.append(f"- {rid}")
                        elif txt:
                            lines.append(f"- {txt}")
                if lines:
                    return "Found the following relevant PCI DSS requirements:\n" + "\n".join(lines) + "\n"
                return "No relevant PCI DSS requirements were found.\n"
            return "No relevant PCI DSS requirements were found.\n"

        if tool_name == "get":
            if status == "not_found":
                requested = None
                if tool_input:
                    requested = tool_input.get("id") or tool_input.get("ids")
                if isinstance(requested, list):
                    requested = ", ".join(requested)
                suffix = f" for ID(s) {requested}" if requested else ""
                return f"No requirement was found{suffix}.\n"

            items = payload if isinstance(payload, list) else [payload]
            lines = []
            for item in items:
                if isinstance(item, dict):
                    rid = (item.get("id") or "").strip()
                    txt = (item.get("text") or "").strip()
                    if txt and len(txt) > 300:
                        txt = txt[:300].rstrip() + "…"
                    if rid and txt:
                        lines.append(f"- {rid}: {txt}")
                    elif rid:
                        lines.append(f"- {rid}")
                    elif txt:
                        lines.append(f"- {txt}")
            if lines:
                return "Retrieved requirement(s):\n" + "\n".join(lines) + "\n"
            return "Retrieved requirement(s).\n"

        # Default fallback for unknown tools
        if status == "success":
            return "Operation completed successfully.\n"
        if status == "error":
            msg = res.get("message") or "An error occurred."
            return f"Tool error: {msg}\n"
        return "Tool completed.\n"
    except Exception:
        return "Tool completed.\n"


async def run_full_pipeline(message: str):
    # 1) Ask LLM for plan — stream with a 'skip' gate (no pre-retrieval context)
    try:
        prompt = format_prompt(
            user_input=message,
            context="",                    # keep planning unbiased; no pre-retrieval
            tool_help=get_tool_overview(), # tool list only
            template_type="main",
        )
        token_stream = await query_llm(prompt, stream=True)
    except Exception as e:
        yield {"type": "error", "stage": "llm_plan", "message": str(e)}
        return

    buffer = ""
    decided = False
    plan_mode = False  # True once we decide to stream the plan

    # STREAMING GATE: only buffer until we know if it's 'skip'
    async for tok in token_stream:
        if decided:
            if plan_mode:
                # Stream plan tokens live
                yield {"type": "token", "text": tok}
            buffer += tok
            continue

        buffer += tok
        stripped = buffer.lstrip()

        # Case 1: JSON plan starting → start streaming immediately
        if stripped.startswith("{") or stripped.startswith("["):
            decided = True
            plan_mode = True
            yield {"type": "stage", "label": "Thinking..."}
            yield {"type": "token", "text": "\n[PLAN] "}
            yield {"type": "token", "text": stripped}
            continue

        # Case 2: starts with 'skip' (maybe) — wait to confirm
        if stripped.lower().startswith("skip"):
            tail = stripped[4:]
            # If any non-whitespace after 'skip', it's NOT skip → plan mode
            if any(ch not in " \t\r\n" for ch in tail):
                decided = True
                plan_mode = True
                yield {"type": "stage", "label": "Thinking..."}
                yield {"type": "token", "text": "\n[PLAN] "}
                yield {"type": "token", "text": stripped}
                continue

        else:
            # First non-space char is something else → stream as plan
            if stripped:
                decided = True
                plan_mode = True
                yield {"type": "stage", "label": "Thinking..."}
                yield {"type": "token", "text": "\n[PLAN] "}
                yield {"type": "token", "text": stripped}
                continue

    # Stream ended — decide based on what we buffered
    plan_text = buffer
    normalized = plan_text.strip().lower()

    if not decided:
        # If we never flipped into plan mode:
        if normalized == "skip":
            # Smalltalk path — no planning UI
            smalltalk_prompt = format_prompt(
                user_input=message,
                context="",
                tool_help="",
                template_type="smalltalk",
            )
            yield {"type": "stage", "label": "Answer"}
            try:
                token_stream = await query_llm(smalltalk_prompt, stream=True)
                async for token in token_stream:
                    yield {"type": "token", "text": token}
            except (ConnectionError, TimeoutError, RuntimeError) as e:
                yield {"type": "error", "stage": "llm_smalltalk", "message": str(e)}
            return
        else:
            # Not skip, but we buffered everything → show plan header now
            yield {"type": "stage", "label": "Thinking..."}
            yield {"type": "token", "text": "\n[PLAN] " + plan_text.strip() + "\n"}
    else:
        if plan_mode:
            # We streamed plan live; ensure a newline terminator
            yield {"type": "token", "text": "\n"}

    # 2) Parse plan → actions
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

    # No 'final answer' path in this design; ignore if parser returns it
    if final_answer:
        yield {"type": "stage", "label": "Producing final answer..."}
        yield {"type": "token", "text": str(final_answer)}
        return

    # 3) Execute actions sequentially
    if actions and len(actions) > MAX_ACTIONS:
        actions = actions[:MAX_ACTIONS]
        yield {
            "type": "info",
            "message": f"Action list truncated to {MAX_ACTIONS} steps for safety.",
        }

    observations: List[Dict[str, Any]] = []
    total_chars = 0

    if not actions:
        # No actions to run; stop here (no follow-up on empty plan)
        yield {
            "type": "error",
            "stage": "validate_plan",
            "message": "Plan contained no actions.",
        }
        return

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
            result = {"status": "error", "tool_name": tool_name, "message": str(e)}

        # Human-readable tool output (no raw JSON)
        summary = _format_tool_output(tool_name, result, tool_input=tool_input)
        yield {"type": "token", "text": summary}

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

    # 4) Follow-up reasoning using all observations
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
