# mcp_server/main.py
import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mcp_server.router import router as ask_router
from mcp_server.tool_dispatcher import tool_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Startup logic (if any)
        yield
    except asyncio.CancelledError:
        # Suppress benign cancellation (e.g., during reload)
        pass
    finally:
        # Shutdown logic (if needed)
        pass


app = FastAPI(lifespan=lifespan)

# ----- CORS (configure via env) -----
# Example: CORS_ALLOW_ORIGINS="https://your-amplify.app,https://www.example.com"
_allow_origins = os.getenv("CORS_ALLOW_ORIGINS", "*").strip()
if _allow_origins == "*":
    origins = ["*"]
else:
    origins = [o.strip() for o in _allow_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,  # set True only if you use explicit origins (not "*")
)

# ----- Health check for App Runner -----
@app.get("/health")
def health():
    return {"ok": True}

# (Optional) simple root
@app.get("/")
def root():
    return {"service": "pci-compliance-agent", "status": "ok"}

# ----- Routers -----
app.include_router(ask_router)
app.include_router(tool_router)
