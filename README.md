# 🛡️ PCI DSS Compliance Agent

This project is a document-aware assistant for PCI DSS (Payment Card Industry Data Security Standard) compliance.  
It combines a Retrieval-Augmented Generation (RAG) pipeline with a planning step and modular tool execution to help users understand and interact with PCI DSS requirements through transparent, structured reasoning and tool-based execution.

![Python](https://img.shields.io/badge/python-3.11+-blue)
![License](https://img.shields.io/badge/license-Apache%202.0-blue)
![Build](https://img.shields.io/badge/build-passing-brightgreen)

---

## 🔧 Key Components

- **Web UI (AWS Amplify)**  
  Browser-based chat interface with support for "Mock Chat" and "Live Mode".  
  Sends user queries to the backend over HTTPS and displays retrieved PCI DSS requirement excerpts by ID or via semantic search.

- **Backend (FastAPI on AWS App Runner)**  
  Hosted in AWS App Runner, container image stored in Amazon ECR.  
  On startup, downloads `pci_index.faiss` (FAISS vector index) and `pci_requirements.db` (SQLite database) from S3 into `/app/data`.  
  Exposes `/healthz` endpoint for AWS App Runner health checks.  
  REST API routes:  
    - `GET /search` — semantic search in FAISS, enriched with SQLite results.  
    - `GET /get_requirement_text` — retrieve requirement text by ID.

- **Data Layer**  
  - FAISS `IndexIDMap` for dense embedding similarity search.  
  - SQLite database storing requirements with IDs (e.g., "10.6", "10.5", "10.2.1") and associated metadata.  
  - Artifacts stored in S3 and loaded at container startup.

- **Retrieval Pipeline**  
  Embeddings generated via `all-MiniLM-L6-v2` (or `text-embedding-3-small` as an alternative).  
  Retrieves top-k relevant chunks from FAISS and enriches them with full requirement text from SQLite.

- **Planning Layer**  
  Before invoking tools, the LLM determines whether they’re needed:  
  - If not, skips tools and answers directly.  
  - If needed, selects the tool (`get` or `search`), prepares arguments, invokes it, and uses the results to compose the final answer.

- **Execution Layer (Tool Dispatcher & MCP Server)**  
  - Validates tool calls and routes them to isolated execution.  
  - Supported tools:
    - `get` — fetch specific requirements by ID from SQLite.
    - `search` — semantic search in vector store, enriched from SQLite.
    - (Planned) `generate_pdf_report`
    - (Planned) `parse_uploaded_document`

---

## 🗂️ Project Structure

```
.
├── agent/                        # LLM logic, models, and prompt templates
│   ├── models/                   # Shared Pydantic schemas
│   │   ├── base.py
│   │   └── requirement.py
│   ├── llm_wrapper.py
│   ├── prompt_formatter.py
│   ├── tool_call_parser.py
│   ├── prompt_template.txt
│   └── followup_template.txt
│
├── cli.py                        # CLI entry point for interactive chat
├── docs/                         # Parsed PCI DSS requirements and taxonomy
│   ├── requirement_index.json
│   ├── parsed_requirements.md
│
├── data/                         # Vector index and document chunks
│   ├── pci_chunks.txt
│   ├── pci_index.faiss
│
├── mcp_server/                   # FastAPI backend for tool execution
│   ├── main.py
│   ├── pipeline.py
│   ├── router.py
│   └── tool_dispatcher.py
│
├── retrieval/                    # FAISS-based retriever logic
│   └── retriever.py
│
├── scripts/                      # One-time setup scripts
│   └── build_index.py
│
├── tools/                        # Tool implementations
│   ├── get.py
│   ├── search.py
│   ├── compare_requirements.py
│   └── recommend_tool.py
│
├── tests/                        # Unit and integration tests
│   └── test_tool_call_parser.py
│
├── cli.log                       # CLI log output
├── .gitignore                    # Git ignore rules
├── requirements.txt              # Python dependencies
├── .pylintrc                     # Pylint config
├── .pre-commit-config.yaml       # Pre-commit hook config
└── README.md                     # Project documentation
```

---


## 🚀 How to Run

If deployed to AWS Amplify, simply visit your Amplify app's URL to use the Web UI.
To run locally:

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the tool server** (in a separate terminal):
   ```bash
   uvicorn mcp_server.main:app --reload
   ```

3. **Run the CLI interface**:
   ```bash
   # Optional: set MCP server URL if not running on localhost:8000
export MCP_API_URL="http://<your-mcp-host>:<port>"

python cli.py
   ```

   Or test using the mock backend:
   ```bash
python cli.py --mock -m "Compare 1.1.2 and 12.5.1"
   ```

4. **Exit** with:
   ```text
   exit
   quit
   ```


## 🧠 What the Agent Can Do

- 🧪 **Test easily** using mock endpoints (`/ask_mock`, `/ask_mock_full`) for UI or CLI without full backend.

- 🔍 **Understand** vague queries like “Help me with encryption”
- 📑 **Retrieve** exact PCI DSS requirement text by ID
- 🧠 **Reason** about tool selection when user input is ambiguous
- 🧭 **Compare** requirements in context with summarized differences
- 🔗 **Stream responses** incrementally with thoughtful follow-up logic

---

## 🧪 Testing

Run static analysis and tests:

```bash
pylint --rcfile=.pylintrc $(git ls-files '*.py')
pytest
```

Optional tools:
- `ruff check .`
- `mypy agent/ tools/`

---

## 🔧 Setup Notes

- To customize the model or backend URL, use the `LLM_MODEL` and `LLM_API_URL` environment variables.

- This project assumes a local Ollama or similar LLM backend is running.
- For vector search, ensure `pci_chunks.txt` and `pci_index.faiss` exist in `./data/`. If not, run:

```bash
python scripts/build_index.py
```

---

---

## ⚙️ Environment Variables

By default, the agent sends prompts to a local LLM endpoint. You can override the model and URL by setting the following environment variables:

| Variable       | Description                                   | Default Value                                         |
|----------------|-----------------------------------------------|-------------------------------------------------------|
| `MCP_API_URL`   | URL of the MCP backend for tool execution            | `http://localhost:8000`    |
| `LLM_API_URL`  | URL of the LLM backend                        | `http://localhost:11434/api/generate`                |
| `LLM_MODEL`    | Model identifier passed to the backend        | `mistral:7b-instruct-v0.3-q4_K_M`                    |
| `FAISS_INDEX_PATH`   | Path to FAISS index file for document retrieval    | `data/pci_index.faiss`     |
| `SQLITE_DB_PATH`    | Path to SQLite database for requirement text | `data/pci_requirements.db` |
| `S3_BUCKET`         | S3 bucket name for artifact storage       | *(required for AWS deployment)* |

You can define them in your shell before launching the CLI:

```bash
export LLM_API_URL="http://localhost:11434/api/generate"
export LLM_MODEL="mistral:7b-instruct-v0.3-q4_K_M"
export MCP_API_URL="http://localhost:8000"
export FAISS_INDEX_PATH="data/custom_index.faiss"
# Optional: set MCP server URL if not running on localhost:8000

python cli.py
```

Or in `.env` if you’re using `python-dotenv` (optional).


## 🤝 Contributing

Clone, set up a virtualenv, install deps, and open PRs or issues.

```bash
git clone https://github.com/Alisher-Bulatov/pci-compliance-agent
cd pci-compliance-agent
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

Sample Prompts:

  # 1) Direct retrieval tests (single-ID get)
    - "What is written in requirement 6.5?"
    - "Give me the text of 2.3"
    - "Show the details for 10.6"
    - "Read me 3.2.1"
    - "What does 12.10 say?"

  # 2) Batch retrieval tests (multi-ID get with order + dedupe)
    - "Show 10.6, 10.5, and 10.2.1"
    - "Give me 1.1.1 and 1.1.2"
    - "Compare 1.2.1, 1.2, and 1.2.1 again"        # expect get:["1.2.1","1.2"] (dedupe, keep first-seen order)
    - "Summarize 3.2 and 4.2 side by side"
    - "Explain 12.5 and 12.5.1 in simple terms"

  # 3) Topic search tests (no explicit IDs → search)
    - "Which PCI DSS rules address anti-phishing protections?"
    - "Find all requirements related to penetration testing"
    - "List the requirements about cryptographic key storage"
    - "What covers centralized time synchronization across systems?"
    - "Show me network intrusion detection/response requirements"

  # 4) Interpretive reasoning tests (ID present → still get)
    - "Is 3.2.1 focused on storage limitations or on transmission security?"
    - "Explain 9.5 in plain terms"
    - "Why is 1.5 critical for protecting the CDE?"
    - "Clarify the difference between 10.6 and 10.5"
    - "Does 2.3 apply to all wireless or only guest Wi-Fi?"

  # 5) Explicit extra-context with IDs (should choose search, not get)
  #    These ask for *related/what’s new/guidance/mapping/evidence* → search:"..."
    - "Find related requirements to 10.6"
    - "What’s new about 3.6.1 in the latest version?"
    - "Show guidance or examples from SAQ/ROC for 11.2.1"
    - "Map 12.6 to ISO/IEC 27001 controls"
    - "What test evidence is expected for 1.1.2?"

  # 6) Mixed / ambiguous to trigger tool choice (IDs sometimes baked into query)
    - "Tell me about secure software development requirements"             # search
    - "Which requirement covers time-synchronization mechanisms?"          # search (likely 10.6)
    - "How should wireless environments be secured according to PCI DSS?"  # search (likely 2.3)
    - "What requirement talks about MFA into the CDE?"                     # search (8.4/8.5)

  # 7) Edge cases the router must handle cleanly
    - "hello"                                   # skip
    - "thanks!"                                 # skip
    - "Show 13"                                 # invalid ID → search (no valid IDs detected)
    - "Explain v4.0.1 changes in 3.x"           # no valid IDs → search
    - "Can you summarize 1.2.1 and 1.2.1?"      # get with dedupe → get:["1.2.1"]
    - "Compare 4.2 and 3.5 quickly"             # get:["4.2","3.5"]

---

## ❓ Troubleshooting

**Q: CLI doesn't respond or crashes on startup?**  
A: Ensure the backend server is running (`uvicorn mcp_server.main:app --reload`). Or use `/ask_mock_full` for mock mode.

**Q: Vector index not found?**  
A: Run:
```bash
python scripts/build_index.py
```

**Q: LLM connection refused?**  
A: Make sure your local model (e.g., Ollama) is running.

## 📜 License

This project is licensed under the [Apache License 2.0](LICENSE).



## 📦 Deployment (AWS)

1. **Build container image** and push to Amazon ECR.
2. **Create AWS App Runner service**:  
   - Set `/healthz` as health check path.  
   - Service listens on port 8080 internally.  
   - Attach IAM role with permissions for ECR and S3 (`ecr:GetAuthorizationToken`, `ecr:BatchGetImage`, `s3:GetObject`).
3. **Deploy frontend** via AWS Amplify, configured with backend URL.
