#!/usr/bin/env sh
set -e

mkdir -p /app/data

# ---- Kick off S3 downloads in the background (non-blocking) ----
if [ -n "${DATA_BUCKET:-}" ] && { [ -n "${FAISS_KEY:-}" ] || [ -n "${DB_KEY:-}" ]; }; then
  echo "[start] Starting background artifact download from s3://$DATA_BUCKET ..."
  (
    python - <<'PY'
import os, boto3, sys

bucket    = os.environ["DATA_BUCKET"]
faiss_key = os.environ.get("FAISS_KEY")
db_key    = os.environ.get("DB_KEY")

s3 = boto3.client("s3")

def dl(key, dst):
    if not key:
        return
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        print(f"[bg-dl] Downloading s3://{bucket}/{key} -> {dst}", flush=True)
        s3.download_file(bucket, key, dst)
        print(f"[bg-dl] Completed: {dst}", flush=True)
    except Exception as e:
        print(f"[bg-dl] WARN: failed to download {key}: {e}", flush=True)

dl(faiss_key, "/app/data/pci_index.faiss")
dl(db_key,   "/app/data/pci_requirements.db")
PY
  ) &
else
  echo "[start] Skipping S3 download (DATA_BUCKET/FAISS_KEY/DB_KEY not set)."
fi

# ---- Start API server immediately so App Runner health check passes ----
PORT="${PORT:-8080}"
WORKERS="${UVICORN_WORKERS:-1}"

echo "[start] Launching uvicorn on 0.0.0.0:${PORT} (workers=${WORKERS})"
exec uvicorn mcp_server.main:app \
  --host 0.0.0.0 \
  --port "${PORT}" \
  --workers "${WORKERS}" \
  --proxy-headers
w