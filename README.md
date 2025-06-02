# PCI DSS Compliance Agent

This project is a document-aware assistant to help with PCI DSS compliance.

It uses a Retrieval-Augmented Generation (RAG) pipeline powered by FAISS to locate relevant PCI DSS content and combines it with LLM-generated reasoning. Tool calls (e.g., for retrieving requirement text) are executed via an MCP Server, making the system modular and extensible.

## 🔧 Key Components

- **FAISS Retriever**: Loads `pci_chunks.txt` and builds a searchable index.
- **LLM Agent**: Uses prompt formatting to trigger tool calls where needed.
- **MCP Server**: Executes tools like `get_requirement_text` via FastAPI.
- **CLI Interface**: Chat with the agent from terminal using `main.py`.

## 🏁 How to Run

1. Install requirements:
   ```bash
   pip install -r requirements.txt
