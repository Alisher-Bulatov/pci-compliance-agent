# 🛡️ PCI DSS Compliance Agent

This project is a document-aware assistant for PCI DSS (Payment Card Industry Data Security Standard) compliance.  
It combines a Retrieval-Augmented Generation (RAG) pipeline with modular tool execution to help users understand and interact with PCI DSS requirements through transparent, structured reasoning and tool-based execution.

![Python](https://img.shields.io/badge/python-3.11+-blue)
![License](https://img.shields.io/badge/license-Unlicensed-lightgrey)
![Build](https://img.shields.io/badge/build-passing-brightgreen)

---

## 🔧 Key Components

- **FAISS Retriever**  
  Uses `pci_chunks.txt` and a prebuilt FAISS index (`pci_index.faiss`) to locate relevant content from PCI DSS documentation.

- **LLM Agent**  
  Leverages structured prompts to determine whether to respond directly or call a tool. Enables reasoning and step-by-step execution.

- **MCP Server (Modular Command Processor)**  
  A FastAPI-based service that handles backend execution of tools such as `get_requirement_text`, `search_by_topic`, and `compare_requirements`.

- **CLI Chat Interface**  
  Launch via `cli.py` to start an interactive, conversational session with the assistant.

- **Tool Auto-Discovery**  
  The agent dynamically detects available tools and routes commands accordingly.

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
│   └── mapping.pkl
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
│   ├── get_requirement_text.py
│   ├── search_by_topic.py
│   ├── compare_requirements.py
│   └── recommend_tool.py
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
| `LLM_API_URL`  | URL of the LLM backend                        | `http://localhost:11434/api/generate`                |
| `LLM_MODEL`    | Model identifier passed to the backend        | `mistral:7b-instruct-v0.3-q4_K_M`                    |

You can define them in your shell before launching the CLI:

```bash
export LLM_API_URL="http://localhost:11434/api/generate"
export LLM_MODEL="mistral:7b-instruct-v0.3-q4_K_M"
python cli.py
```

Or in `.env` if you’re using `python-dotenv` (optional).


## 🤝 Contributing

Clone, set up a virtualenv, install deps, and open PRs or issues.

```bash
git clone (https://github.com/Alisher-Bulatov/pci-compliance-agent)
cd pci-compliance-agent
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 🔍 Sample Prompts

Try these inside the CLI:

```text
hello
What does 3.2.1 say?
Can you show me the wording of requirement 1.1.2?
Compare requirements 1.1.2 and 12.5.1
Help me understand encryption requirements
What should I consider for secure design?
What about segmentation boundaries?
Is 3.2.1 about sensitive data?
I already know 3.2.1 is about not storing sensitive auth data, but what else should I know?
```

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

None
