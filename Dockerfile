# Dockerfile
FROM python:3.11-slim

ENV TRANSFORMERS_CACHE=/root/.cache/huggingface
WORKDIR /app

RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-warm the embedding model to avoid first-request stalls
RUN python - <<'PY'\nfrom sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')\nPY

# Copy backend code & data
COPY mcp_server ./mcp_server
COPY agent ./agent
COPY retrieval ./retrieval
COPY tools ./tools

# FAISS + DB files (adjust if your paths differ)
COPY pci_index.faiss ./data/pci_index.faiss
COPY pci_requirements.db ./data/pci_requirements.db
# (If you also have a mapping file, uncomment)
# COPY mapping.pkl ./data/mapping.pkl

ENV PORT=8080
EXPOSE 8080

# CORS (override in App Runner)
ENV CORS_ALLOW_ORIGINS="*"

# LLM defaults (override in App Runner)
ENV LLM_API_URL="http://localhost:11434/api/generate"
ENV LLM_MODEL="qwen2.5:7b-instruct"

CMD ["python", "-m", "uvicorn", "mcp_server.main:app", "--host", "0.0.0.0", "--port", "8080"]
