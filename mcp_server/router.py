import json
import asyncio
import random
import time
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent.llm_wrapper import query_llm
from mcp_server.pipeline import run_full_pipeline

router = APIRouter()

# --- helpers ---------------------------------------------------------------

def _clear_caches_lazy():
    # Lazy import so router import never drags in retrieval deps
    from retrieval.retriever import clear_caches as _clear
    _clear()


# --- GET /ask — Raw LLM response (SSE/EventSource) -------------------------

@router.get("/ask")
async def ask_stream_handler(request: Request):
    message = request.query_params.get("message", "")

    async def event_stream():
        try:
            async for token in query_llm(message, stream=True):
                # stop if client disconnected
                if await request.is_disconnected():
                    break
                yield f"data: {token}\n\n"
        except asyncio.CancelledError:
            # client dropped; just exit quietly
            pass

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# --- POST /ask_full — JSON ND streaming -----------------------------------

class AskRequest(BaseModel):
    message: str


@router.post("/ask_full")
async def ask_full_handler(payload: AskRequest, request: Request):
    message = payload.message

    async def stream():
        try:
            async for item in run_full_pipeline(message):
                if await request.is_disconnected():
                    break
                yield json.dumps(item) + "\n"
        except asyncio.CancelledError:
            pass

    return StreamingResponse(stream(), media_type="application/x-ndjson")


# --- GET /ask_mock — mock SSE ---------------------------------------------

@router.get("/ask_mock")
def ask_mock_handler(request: Request):
    _message = request.query_params.get("message", "")

    def event_stream():
        for token in ["Mock response", " continues", "..."]:
            yield f"data: {token}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# --- POST /ask_mock_full — mock NDJSON ------------------------------------

@router.post("/ask_mock_full")
async def ask_mock_full_handler(payload: AskRequest, request: Request):
    _message = payload.message

    async def stream():
        start = time.perf_counter()

        await asyncio.sleep(random.uniform(0.1, 0.3))
        yield json.dumps({"type": "stage", "label": "Thinking..."}) + "\n"
        await asyncio.sleep(random.uniform(0.1, 0.3))

        for token in ["This ", "is ", "a ", "mock ", "response."]:
            if await request.is_disconnected():
                break
            yield json.dumps({"type": "token", "text": token}) + "\n"
            await asyncio.sleep(random.uniform(0.05, 0.2))

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

        yield json.dumps({"type": "token", "text": "\n"}) + "\n"

        followups = [
            "Hope that helps clarify your query.",
            "Let me know if you'd like to compare more.",
            "This should give you a quick overview.",
            "You're doing great — feel free to explore further.",
        ]
        for word in random.choice(followups).split():
            if await request.is_disconnected():
                break
            yield json.dumps({"type": "token", "text": word + " "}) + "\n"
            await asyncio.sleep(random.uniform(0.05, 0.15))

        elapsed = time.perf_counter() - start
        yield json.dumps({"type": "info", "message": f"Mock response completed in {elapsed:.2f} seconds"}) + "\n"

    return StreamingResponse(stream(), media_type="application/x-ndjson")


# --- Reload retriever (clears FAISS/model caches) -------------------------

@router.post("/reload_index")
def reload_index():
    _clear_caches_lazy()
    return {"status": "Caches cleared and ready for reload."}
