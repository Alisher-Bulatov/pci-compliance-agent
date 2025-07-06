# mcp_server/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio

from mcp_server.router import router as ask_router
from mcp_server.tool_dispatcher import tool_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Startup logic (if any)
        yield
    except asyncio.CancelledError:
        # Suppress benign cancellation caused by reload
        pass
    finally:
        # Shutdown logic (if needed)
        pass


app = FastAPI(lifespan=lifespan)

# Enable CORS for frontend integration (Vite runs on port 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(ask_router)
app.include_router(tool_router)
