import json
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from agent.llm_wrapper import query_llm
from mcp_server.pipeline import run_full_pipeline

router = APIRouter()


# 🔹 GET /ask — Raw LLM response (for EventSource/browser dev)
@router.get("/ask")
def ask_stream_handler(request: Request):
    message = request.query_params.get("message", "")

    def event_stream():
        for token in query_llm(message, stream=True):
            yield f"data: {token}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# 🔹 GET /ask_full — JSON ND streaming (structured events for CLI/frontend)
@router.get("/ask_full")
async def ask_full_handler(request: Request):
    message = request.query_params.get("message", "")

    async def stream():
        async for item in run_full_pipeline(message):
            yield json.dumps(item) + "\n"

    return StreamingResponse(stream(), media_type="application/x-ndjson")


# 🔹 GET /ask_mock — mock LLM response (for EventSource/browser dev)
@router.get("/ask_mock")
def ask_mock_handler(request: Request):
    _message = request.query_params.get("message", "")

    def event_stream():
        for token in ["Mock response", " continues", "..."]:
            yield f"data: {token}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# 🔹 GET /ask_mock_full — mock JSON ND streaming (structured events for CLI/frontend dev)
@router.get("/ask_mock_full")
def ask_mock_full_handler(request: Request):
    def stream():
        for item in [
            {"type": "tool_result", "result": "Mock comparison output"},
            {"type": "message", "content": "This is a follow-up message."},
        ]:
            yield json.dumps(item) + "\n"

    return StreamingResponse(stream(), media_type="application/x-ndjson")
