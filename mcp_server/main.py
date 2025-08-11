import os
from contextlib import asynccontextmanager
from typing import List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mcp_server.router import router as ask_router
from mcp_server.tool_dispatcher import tool_router

def parse_origins(val: str | None) -> List[str]:
    v = (val or "").strip()
    if not v or v == "*":
        return ["*"]
    return [p.strip() for p in v.split(",") if p.strip()]

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(lifespan=lifespan)

origins = parse_origins(os.getenv("CORS_ALLOW_ORIGINS", "*"))
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

@app.on_event("startup")
async def _log_cors():
    print(f"[mcp_server] CORS allow_origins: {origins}")

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/")
def root():
    return {"service": "pci-compliance-agent", "status": "ok"}

app.include_router(ask_router)
app.include_router(tool_router)
