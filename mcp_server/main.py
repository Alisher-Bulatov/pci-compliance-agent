
import os
import threading
import time
from contextlib import asynccontextmanager
from typing import List, Callable

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from mcp_server.router import router as ask_router
from mcp_server.tool_dispatcher import tool_router

# ------------ Config ------------
PORT = int(os.getenv("PORT", "8080"))
CORS_ALLOW_ORIGINS = os.getenv("CORS_ALLOW_ORIGINS", "*")

# Artifacts we consider as "ready" signals (adjust to your project)
DATA_DIR = os.getenv("DATA_DIR", "/app/data")
FAISS_FILE = os.getenv("FAISS_LOCAL_PATH", os.path.join(DATA_DIR, "pci_index.faiss"))
DB_FILE = os.getenv("DB_LOCAL_PATH", os.path.join(DATA_DIR, "pci_requirements.db"))
REQUIRE_FILES = [FAISS_FILE, DB_FILE]

# If true, we won't block readiness on files; only log a warning
READINESS_SOFT = os.getenv("READINESS_SOFT", "false").lower() in ("1", "true", "yes")

# ------------ App init ------------
app = FastAPI(title="PCI Compliance Agent")

_ready = threading.Event()
_started_at = time.time()

def parse_origins(val: str | None) -> List[str]:
    v = (val or "").strip()
    if not v or v == "*":
        return ["*"]
    if "," in v:
        return [s.strip() for s in v.split(",") if s.strip()]
    return [v]

origins = parse_origins(CORS_ALLOW_ORIGINS)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------ Health ------------
@app.get("/healthz")
def healthz():
    """Liveness: server is up and can answer HTTP."""
    return {"ok": True, "uptime_sec": round(time.time() - _started_at, 3)}

@app.get("/readyz")
def readyz():
    """Readiness: heavy dependencies available / warmed."""
    if _ready.is_set():
        return {"ready": True}
    return JSONResponse({"ready": False}, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)

# ------------ Gate routes until ready ------------
ALWAYS_OK_PATHS = {"/", "/healthz", "/readyz", "/docs", "/openapi.json"}

@app.middleware("http")
async def readiness_gate(request: Request, call_next: Callable):
    path = request.url.path
    if path in ALWAYS_OK_PATHS or path.startswith("/static/"):
        return await call_next(request)
    if not _ready.is_set():
        return JSONResponse(
            {"detail": "Service warming up. Try again shortly."},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            headers={"Retry-After": "10"},
        )
    return await call_next(request)

# ------------ Root ------------
@app.get("/")
def root():
    return {"service": "pci-compliance-agent", "status": "ok"}

# ------------ Include routers ------------
app.include_router(ask_router)
app.include_router(tool_router)

# ------------ Background warmup ------------
def _log(msg: str):
    print(f"[warmup] {msg}", flush=True)

def check_files(paths: list[str]) -> bool:
    return all(os.path.exists(p) for p in paths if p)

def do_warmup():
    """
    Wait for artifacts from start.sh (which downloads S3 in background)
    and perform any one-time lazy initializations that are safe in background.
    """
    start = time.time()
    deadline = start + int(os.getenv("READINESS_MAX_WAIT_SEC", "600"))  # 10m default

    # Fast path: if we don't require files, become ready immediately.
    if READINESS_SOFT and not any(REQUIRE_FILES):
        _log("READINESS_SOFT=true and no required files. Marking ready immediately.")
        _ready.set()
        return

    # Poll for required files, but don't block forever.
    while time.time() < deadline:
        if check_files(REQUIRE_FILES):
            _log(f"All required files present. (t+{int(time.time()-start)}s)")
            break
        missing = [p for p in REQUIRE_FILES if p and not os.path.exists(p)]
        _log(f"Waiting for artifacts: missing={missing}")
        time.sleep(2)

    if not check_files(REQUIRE_FILES):
        if READINESS_SOFT:
            _log("Missing artifacts but READINESS_SOFT=true. Marking ready anyway.")
        else:
            _log("Required artifacts missing at deadline. Marking ready to avoid deploy block, "
                 "but requests will still be gated by middleware until files appear.")
    # Any additional non-blocking initializations can go here (e.g., touch caches)

    _ready.set()

@app.on_event("startup")
def schedule_warmup():
    t = threading.Thread(target=do_warmup, name="warmup", daemon=True)
    t.start()
