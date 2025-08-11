#!/usr/bin/env sh
set -eu

mkdir -p /app/data

# Download artifacts from S3 if env vars are set
if [ -n "${DATA_BUCKET:-}" ] && [ -n "${FAISS_KEY:-}" ]; then
python - <<'PY'
import os, boto3
bucket = os.environ["DATA_BUCKET"]
faiss_key = os.environ.get("FAISS_KEY")
db_key    = os.environ.get("DB_KEY")
s3 = boto3.client("s3")

def dl(key, dst):
    if not key:
        return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    print(f"Downloading s3://{bucket}/{key} -> {dst}", flush=True)
    s3.download_file(bucket, key, dst)

dl(faiss_key, "/app/data/pci_index.faiss")
dl(db_key,   "/app/data/pci_requirements.db")
PY
fi

exec python -m uvicorn mcp_server.main:app --host 0.0.0.0 --port "${PORT:-8080}"
