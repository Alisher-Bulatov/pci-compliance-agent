from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json

from agent.llm_wrapper import query_llm
from mcp_server.pipeline import run_full_pipeline, run_full_pipeline_verbose

router = APIRouter()

# 🔹 GET /ask — Raw LLM response (for EventSource/browser dev)
@router.get("/ask")
def ask_stream_handler(request: Request):
    message = request.query_params.get("message", "")

    def event_stream():
        for token in query_llm(message, stream=True):
            yield f"data: {token}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# 🔹 GET /ask_full — Full pipeline via query param (CLI/dev mode)
@router.get("/ask_full")
def ask_full_handler(request: Request):
    message = request.query_params.get("message", "")

    def stream():
        for chunk in run_full_pipeline(message):
            yield chunk

    return StreamingResponse(stream(), media_type="text/plain")


# 🔹 POST /ask_full — Full pipeline for frontend integration (JSON input)
class AskRequest(BaseModel):
    message: str

@router.post("/ask_full")
def ask_full_post_handler(req: AskRequest):
    def stream():
        for token in run_full_pipeline(req.message):
            yield token

    return StreamingResponse(stream(), media_type="text/plain")


# 🔹 GET /ask_full_verbose — JSON ND streaming (structured events for CLI/frontend)
@router.get("/ask_full_verbose")
def ask_full_verbose_handler(request: Request):
    message = request.query_params.get("message", "")

    def stream():
        for item in run_full_pipeline_verbose(message):
            yield json.dumps(item) + "\n"

    return StreamingResponse(stream(), media_type="application/x-ndjson")
