# main.py
from fastapi import FastAPI
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
app.include_router(ask_router)
app.include_router(tool_router)
