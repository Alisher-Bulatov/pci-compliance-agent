from fastapi import FastAPI
from mcp_server.router import router as ask_router
from mcp_server.tool_dispatcher import tool_router

app = FastAPI()
app.include_router(ask_router)
app.include_router(tool_router)
