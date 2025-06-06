# 🛡️ PCI DSS Compliance Agent

This project is a document-aware assistant for PCI DSS compliance.  
It uses a Retrieval-Augmented Generation (RAG) pipeline and modular tool execution to answer questions about PCI DSS requirements in a helpful, transparent, and interactive way.

---

## 🔧 Project Structure

```
.
├── agent/                # Core LLM wrapper, prompt logic, tool call parser
│   ├── llm_wrapper.py
│   ├── prompt_formatter.py
│   ├── tool_call_parser.py
│   └── *.txt             # Prompt templates and followup format

├── cli.py               # CLI-based chat interface (entry point)

├── data/                # Vector index and document mappings
│   ├── pci_chunks.txt
│   ├── pci_index.faiss
│   └── mapping.pkl

├── mcp_server/          # FastAPI server for executing tools
│   ├── main.py
│   ├── pipeline.py
│   ├── router.py
│   └── tool_dispatcher.py

├── retrieval/           # FAISS-based semantic retriever
│   └── retriever.py

├── scripts/             # Index build and setup utilities
│   └── build_index.py

├── tools/               # Tool implementations
│   ├── get_requirement_text.py
│   ├── search_by_topic.py
│   ├── compare_requirements.py
│   └── recommend_tool.py

├── requirements.txt
└── README.md
```

---

## 🚀 How to Run

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Start the tool server (in another terminal):
   ```bash
   uvicorn mcp_server.main:app --reload
   ```

3. Run the CLI interface:
   ```bash
   python cli.py
   ```

4. Type `exit` or `quit` to end the session.

---

## 🧠 Assistant Capabilities

The agent uses LLM reasoning to:

- Answer questions about PCI DSS requirement texts
- Search for relevant topics using embeddings
- Compare multiple requirements
- Recommend appropriate tools when user intent is ambiguous

All logic follows a strict tool-call discipline.

### ✅ Current Supported Tools

| Tool Name              | Description |
|------------------------|-------------|
| `get_requirement_text` | Retrieves exact text of a specific requirement (e.g., 3.2.1) |
| `search_by_topic`      | Retrieves top relevant requirements for a topic (e.g., encryption, firewalls) |
| `compare_requirements` | Compares the full text of two or more requirement IDs |
| `recommend_tool`       | Suggests the best tool to use when the user input is vague or exploratory |

---

## 🔍 Sample Prompts

Try these in the CLI:

```text
hello
What does 3.2.1 say?
Can you compare 1.1.2 and 12.5.1?
Search for authentication requirements
```

---

