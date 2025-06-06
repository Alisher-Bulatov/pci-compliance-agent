# 🛡️ PCI DSS Compliance Agent

This project is a document-aware assistant for PCI DSS compliance.  
It combines a Retrieval-Augmented Generation (RAG) pipeline with modular tool execution to help users understand and interact with PCI DSS requirements in a transparent and intelligent way.

---

## 🔧 Key Components

- **FAISS Retriever**:  
  Uses `pci_chunks.txt` and a prebuilt FAISS index (`pci_index.faiss`) to locate relevant content from PCI DSS documentation.

- **LLM Agent**:  
  Leverages structured prompts to determine whether to respond directly or call a tool. Enables reasoning and step-by-step execution.

- **MCP Server (Modular Command Processor)**:  
  A FastAPI-based service that handles backend execution of tools such as `get_requirement_text`, `search_by_topic`, and `compare_requirements`.

- **CLI Chat Interface**:  
  Launch via `cli.py` to start an interactive, conversational session with the assistant.

---

## 🗂️ Project Structure

```
.
├── agent/                # LLM logic, prompt templates, and tool call parser
│   ├── llm_wrapper.py
│   ├── prompt_formatter.py
│   ├── tool_call_parser.py
│   └── *.txt             # Prompt templates and followup formats
├── cli.py                # CLI entry point
├── data/                 # Vector index and document chunks
│   ├── pci_chunks.txt
│   ├── pci_index.faiss
│   └── mapping.pkl
├── mcp_server/           # FastAPI backend for tool execution
│   ├── main.py
│   ├── pipeline.py
│   ├── router.py
│   └── tool_dispatcher.py
├── retrieval/            # FAISS retriever wrapper
│   └── retriever.py
├── scripts/              # One-time setup scripts
│   └── build_index.py
├── tools/                # Tool definitions
│   ├── get_requirement_text.py
│   ├── search_by_topic.py
│   ├── compare_requirements.py
│   └── recommend_tool.py
├── requirements.txt
└── README.md
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

4. **Exit** with:
   ```text
   exit
   quit
   ```

---

## 🧠 Assistant Capabilities

The agent uses structured LLM reasoning to:

- Retrieve the exact text of PCI DSS requirements by ID
- Perform semantic searches for relevant topics (e.g., "firewalls", "encryption")
- Compare multiple requirements to highlight differences
- Suggest which tool to use based on vague queries

All logic is built around explicit tool calls and reproducible outputs.

### ✅ Available Tools

| Tool Name              | Description |
|------------------------|-------------|
| `get_requirement_text` | Retrieves the full text of a specific requirement (e.g., `3.2.1`) |
| `search_by_topic`      | Finds top requirements related to a keyword/topic |
| `compare_requirements` | Compares full text of multiple requirement IDs |
| `recommend_tool`       | Infers the best tool to use for ambiguous queries |

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

## 📜 License

None

---
