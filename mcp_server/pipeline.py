# mcp_server/pipeline.py

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from tools import get_tool_overview
from agent.llm_wrapper import query_llm
from agent.prompt_formatter import format_prompt
from agent.tool_call_parser import extract_tool_call, normalize_actions
from mcp_server.tool_dispatcher import handle_tool_call_async

# Safety limits so the follow-up prompt can't explode
MAX_ACTIONS = 6
MAX_PER_OBS_CHARS = 6000
MAX_TOTAL_OBS_CHARS = 24000


def _truncate_for_prompt(s: str | None, limit: int) -> str:
    if not s:
        return ""
    if len(s) <= limit:
        return s
    return s[: limit - 20] + "... [truncated]"


def _format_tool_output(
    tool_name: str,
    result_obj: Any,
    tool_input: Dict[str, Any] | None = None,
) -> str:
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
                lines: List[str] = []
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
                    return "Retrieved materials\n\n" + "\n" + "\n".join(lines) + "\n"
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
            lines: List[str] = []
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
                return "\n" + "\n".join(lines) + "\n"
            return "\nRetrieved requirement(s).\n"

        # Default fallback for unknown tools
        if status == "success":
            return "Operation completed successfully.\n"
        if status == "error":
            msg = res.get("message") or "An error occurred."
            return f"Tool error: {msg}\n"
        return "Tool completed.\n"
    except Exception:
        return "Tool completed.\n"


# ---- Normalization helpers ---------------------------------------------------

_ID_REGEX = re.compile(r"\b\d+(?:\.\d+){0,3}\b")

def _extract_pci_ids(s: str) -> List[str]:
    if not s:
        return []
    return [m.group(0) for m in _ID_REGEX.finditer(s)]


def _normalize_get_action(action: Dict[str, Any]) -> Dict[str, Any]:
    if (action or {}).get("tool_name") != "get":
        return action

    tin = (action.get("tool_input") or {}) if isinstance(action.get("tool_input"), dict) else {}
    id_val = tin.get("id")
    ids_val = tin.get("ids")

    found: List[str] = []
    if isinstance(ids_val, list):
        for x in ids_val:
            if isinstance(x, str):
                found.extend(_extract_pci_ids(x))
    elif isinstance(ids_val, str):
        found.extend(_extract_pci_ids(ids_val))

    if isinstance(id_val, str):
        found.extend(_extract_pci_ids(id_val))
    elif isinstance(id_val, list):
        for x in id_val:
            if isinstance(x, str):
                found.extend(_extract_pci_ids(x))

    # de-dup, preserve order
    seen = set()
    clean: List[str] = []
    for rid in found:
        if rid not in seen:
            clean.append(rid)
            seen.add(rid)

    if not clean and isinstance(id_val, str) and _ID_REGEX.fullmatch(id_val):
        clean = [id_val]

    if not clean:
        return action

    if len(clean) == 1:
        action["tool_input"] = {"id": clean[0]}
    else:
        action["tool_input"] = {"ids": clean}
    return action


def _normalize_actions_list(actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for a in actions or []:
        if not isinstance(a, dict):
            continue
        if a.get("tool_name") == "get":
            a = _normalize_get_action(a)
        out.append(a)
    return out


async def run_full_pipeline(message: str):
    """
    Orchestrates: plan → tools → compose. Yields streaming dict events:
    - {type:'stage', label:'Routing'|'Tools'|'Answer'}
    - {type:'token', segment:'materials'|'answer', text:'...'}
    - {type:'error', stage:'...', message:'...'}
    """
    # 1) Ask LLM for compact plan — BUFFER tokens first (so skip hides panel)
    try:
        prompt = format_prompt(
            user_input=message,
            context="",
            tool_help=get_tool_overview(),
            template_type="main",
        )
        token_stream = await query_llm(prompt, stream=True)
    except Exception as e:
        yield {"type": "error", "stage": "llm_plan", "message": str(e)}
        return

    plan_buffer = ""
    async for tok in token_stream:
        plan_buffer += tok

    plan_text = plan_buffer.strip()

    # 2) Parse plan → actions or skip
    try:
        parsed = extract_tool_call(plan_text)
        if isinstance(parsed, dict) and parsed.get("skip") is True:
            # Smalltalk / direct answer path — DO NOT show materials panel
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
                    yield {"type": "token", "segment": "answer", "text": token}
            except (ConnectionError, TimeoutError, RuntimeError) as e:
                yield {"type": "error", "stage": "llm_smalltalk", "message": str(e)}
            return

        actions, final_answer = normalize_actions(parsed)

    except Exception as e:
        yield {
            "type": "error",
            "stage": "parse_plan",
            "message": f"Failed to parse route: {e}",
        }
        return

    # If router already produced final text with no tools, just answer
    if (not actions) and final_answer:
        yield {"type": "stage", "label": "Answer"}
        try:
            token_stream = await query_llm(final_answer, stream=True)
            async for token in token_stream:
                yield {"type": "token", "segment": "answer", "text": token}
        except (ConnectionError, TimeoutError, RuntimeError) as e:
            yield {"type": "error", "stage": "llm_followup", "message": str(e)}
        return

    # Safety cap on action count
    if actions and len(actions) > MAX_ACTIONS:
        actions = actions[:MAX_ACTIONS]
        yield {
            "type": "info",
            "message": f"Action list truncated to {MAX_ACTIONS} steps for safety.",
        }

    # Normalize actions (fix messy get inputs like `get:"10.5" "10.6"`)
    actions = _normalize_actions_list(actions)

    if not actions:
        yield {
            "type": "error",
            "stage": "validate_plan",
            "message": "Plan contained no actions.",
        }
        return

    # 3) Execute actions sequentially
    yield {"type": "stage", "label": "Routing"}
    if plan_text:
        yield {"type": "token", "segment": "materials", "text": plan_text + "\n"}

    yield {"type": "stage", "label": "Tools"}

    observations: List[Dict[str, Any]] = []
    total_chars = 0

    for idx, action in enumerate(actions, 1):
        tool_name = action.get("tool_name")
        tool_input = action.get("tool_input", {}) or {}

        if not tool_name or not isinstance(tool_input, dict):
            yield {
                "type": "error",
                "stage": "tool_validation",
                "message": f"Invalid action at step {idx}: {action}",
            }
            continue

        try:
            result = await handle_tool_call_async(tool_name, tool_input)
        except Exception as e:
            yield {
                "type": "error",
                "stage": "tool_execution",
                "message": f"{tool_name} failed: {e}",
            }
            result = {"status": "error", "tool_name": tool_name, "message": str(e)}

        # Human-readable tool output (no raw JSON)
        summary = _format_tool_output(tool_name, result, tool_input=tool_input)
        yield {"type": "token", "segment": "materials", "text": summary}

        # Keep both raw and truncated strings for follow-up
        try:
            raw_json_str = json.dumps(result, ensure_ascii=False)
        except Exception:
            raw_json_str = str(result)

        result_str = _truncate_for_prompt(raw_json_str, MAX_PER_OBS_CHARS)
        total_chars += len(result_str)
        if total_chars > MAX_TOTAL_OBS_CHARS:
            result_str = "[omitted due to total size limit]"

        # Extract quick, machine-readable IDs for the follow-up composer
        ids_for_prompt: List[str] = []
        try:
            if isinstance(result, dict):
                payload = result.get("result")
                if isinstance(payload, list):
                    for it in payload:
                        if isinstance(it, dict) and it.get("id"):
                            ids_for_prompt.append(str(it["id"]).strip())
                elif isinstance(payload, dict) and payload.get("id"):
                    ids_for_prompt.append(str(payload["id"]).strip())
        except Exception:
            ids_for_prompt = []

        # Append observation
        observations.append({
            "tool": tool_name,
            "input": tool_input,
            "status": (result.get("status") if isinstance(result, dict) else None),
            "meta": (result.get("meta") if isinstance(result, dict) else None),
            "ids": ids_for_prompt,
            "result": result_str,
            "raw_result": result,
        })

        if total_chars > MAX_TOTAL_OBS_CHARS:
            yield {
                "type": "info",
                "message": "Further observations omitted due to size limits.",
            }
            break

    # 4) Follow-up reasoning using all observations
    yield {"type": "stage", "label": "Answer"}

    tool_result_str = json.dumps(observations, ensure_ascii=False)
    followup_prompt = format_prompt(
        user_input=message,
        context="",
        tool_help="",
        template_type="followup",
        tool_result=tool_result_str,
    )

    try:
        token_stream = await query_llm(followup_prompt, stream=True)
        async for token in token_stream:
            yield {"type": "token", "segment": "answer", "text": token}
    except (ConnectionError, TimeoutError, RuntimeError) as e:
        yield {"type": "error", "stage": "llm_followup", "message": str(e)}
