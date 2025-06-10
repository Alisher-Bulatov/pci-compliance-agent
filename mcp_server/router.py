import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent.llm_wrapper import query_llm
from mcp_server.pipeline import run_full_pipeline

router = APIRouter()


# 🔹 GET /ask — Raw LLM response (for EventSource/browser dev)
@router.get("/ask")
def ask_stream_handler(request):
    message = request.query_params.get("message", "")

    def event_stream():
        for token in query_llm(message, stream=True):
            yield f"data: {token}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# 🔹 POST /ask_full — JSON ND streaming (structured events for CLI/frontend)
class AskRequest(BaseModel):
    message: str


@router.post("/ask_full")
async def ask_full_handler(payload: AskRequest):
    message = payload.message

    async def stream():
        async for item in run_full_pipeline(message):
            yield json.dumps(item) + "\n"

    return StreamingResponse(stream(), media_type="application/x-ndjson")


# 🔹 GET /ask_mock — mock LLM response (for EventSource/browser dev)
@router.get("/ask_mock")
def ask_mock_handler(request):
    _message = request.query_params.get("message", "")

    def event_stream():
        for token in ["Mock response", " continues", "..."]:
            yield f"data: {token}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# 🔹 POST /ask_mock_full — mock JSON ND streaming (structured events for CLI/frontend dev)
@router.post("/ask_mock_full")
async def ask_mock_full_handler(payload: AskRequest):
    _message = payload.message  # optionally echo/use it

    async def stream():
        for item in [
            {"type": "stage", "label": "Retrieving related requirements"},
            {"type": "stage", "label": "Thinking..."},
            {"type": "token", "text": "This "},
            {"type": "token", "text": "is "},
            {"type": "token", "text": "a "},
            {"type": "token", "text": "mock "},
            {"type": "token", "text": "response."},
            {
                "type": "tool_result",
                "result": {
                    "id": "1.1.2",
                    "text": "Mocked requirement comparison.",
                    "tags": ["network", "policy"],
                },
            },
            {"type": "message", "content": "This is a follow-up message."},
        ]:
            yield json.dumps(item) + "\n"

    return StreamingResponse(stream(), media_type="application/x-ndjson")
