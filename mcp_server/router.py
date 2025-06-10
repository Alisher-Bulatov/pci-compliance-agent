import json
import asyncio
import random
import time
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
    _message = payload.message

    async def stream():
        start = time.perf_counter()

        yield json.dumps(
            {"type": "stage", "label": "Retrieving related requirements"}
        ) + "\n"
        await asyncio.sleep(random.uniform(0.1, 0.3))

        yield json.dumps({"type": "stage", "label": "Thinking..."}) + "\n"
        await asyncio.sleep(random.uniform(0.1, 0.3))

        for token in ["This ", "is ", "a ", "mock ", "response."]:
            yield json.dumps({"type": "token", "text": token}) + "\n"
            await asyncio.sleep(random.uniform(0.05, 0.2))

        # Randomized tool result
        sample_results = [
            {
                "id": "1.1.2",
                "text": "Mocked firewall requirement.",
                "tags": random.sample(["network", "firewall", "infrastructure"], k=2),
            },
            {
                "id": "12.5.1",
                "text": "Mocked compliance responsibility.",
                "tags": random.sample(["compliance", "management", "oversight"], k=2),
            },
        ]
        random.shuffle(sample_results)

        yield json.dumps(
            {
                "type": "tool_result",
                "text": {
                    "status": "success",
                    "tool_name": "compare_requirements",
                    "result": sample_results,
                },
            }
        ) + "\n"
        await asyncio.sleep(random.uniform(0.1, 0.2))

        # Blank line for readability before follow-up
        yield json.dumps({"type": "token", "text": "\n"}) + "\n"

        # Randomized follow-up message
        followups = [
            "Hope that helps clarify your query.",
            "Let me know if you'd like to compare more.",
            "This should give you a quick overview.",
            "You're doing great — feel free to explore further.",
        ]
        followup_phrase = random.choice(followups)
        for word in followup_phrase.split():
            yield json.dumps({"type": "token", "text": word + " "}) + "\n"
            await asyncio.sleep(random.uniform(0.05, 0.15))

        # Final info event
        elapsed = time.perf_counter() - start
        yield json.dumps(
            {
                "type": "info",
                "message": f"Mock response completed in {elapsed:.2f} seconds",
            }
        ) + "\n"

    return StreamingResponse(stream(), media_type="application/x-ndjson")
