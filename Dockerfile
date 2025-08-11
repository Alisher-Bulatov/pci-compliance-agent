# Dockerfile
FROM python:3.11-slim

ENV TRANSFORMERS_CACHE=/root/.cache/huggingface \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

# System deps (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
  && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir boto3

# (Optional) pre-warm the embedding model to avoid first-request stalls
# Comment out if CI/build time is an issue.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy backend code
COPY mcp_server ./mcp_server
COPY agent ./agent
COPY retrieval ./retrieval
COPY tools ./tools

# Start script: normalize CRLF and make executable (prevents exec format errors)
COPY start.sh ./start.sh
RUN sed -i 's/\r$//' start.sh && chmod +x start.sh

# Service config
ENV PORT=8080
EXPOSE 8080

# CORS (override in App Runner)
ENV CORS_ALLOW_ORIGINS="*"

# LLM defaults (override in App Runner)
ENV LLM_API_URL="http://localhost:11434/api/generate"
ENV LLM_MODEL="qwen2.5:7b-instruct"

# Data download envs (set these in App Runner)
# ENV DATA_BUCKET=""
# ENV FAISS_KEY=""
# ENV DB_KEY=""

# Run through /bin/sh to avoid shebang/encoding issues
CMD ["/bin/sh", "./start.sh"]
