FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TRANSFORMERS_CACHE=/root/.cache/huggingface

WORKDIR /app

# Minimal build deps
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir boto3

# Optional: pre-warm embeddings model (comment this out if build time is an issue)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# App code
COPY mcp_server ./mcp_server
COPY agent ./agent
COPY retrieval ./retrieval
COPY tools ./tools

# Start script
COPY start.sh ./start.sh
RUN sed -i 's/\r$//' start.sh && chmod +x start.sh

# Service config (App Runner probes port 8080)
ENV PORT=8080
EXPOSE 8080

# Defaults (override in App Runner if needed)
ENV CORS_ALLOW_ORIGINS="*"
ENV LLM_API_URL="http://localhost:11434/api/generate"
ENV LLM_MODEL="qwen2.5:7b-instruct"

CMD ["/bin/sh", "./start.sh"]
