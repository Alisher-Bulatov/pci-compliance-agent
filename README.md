# 🛡️ PCI DSS Compliance Agent

This project is a document-aware assistant for PCI DSS compliance.  
It uses a Retrieval-Augmented Generation (RAG) pipeline and modular tool execution to answer questions about PCI DSS requirements in a helpful, transparent, and interactive way.

---

🔧 Key Components
FAISS Retriever
Uses pci_chunks.txt and a prebuilt index (pci_index.faiss) to locate relevant content from PCI DSS documentation.

LLM Agent
Uses structured prompts to decide when to call tools or answer directly. Supports both reasoning and execution steps.

MCP Server
A FastAPI service that executes tools like get_requirement_text, search_by_topic, or compare_requirements.

CLI Chat Interface
Run main.py to start a conversation. You’ll get responses, tool calls, and updates interactively.

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
Can you show me the wording of requirement 1.1.2?
Compare requirements 1.1.2 and 12.5.1
Help me understand encryption requirements
What should I consider for secure design?
What about segmentation boundaries?
Is 3.2.1 about sensitive data?
I already know 3.2.1 is about not storing sensitive auth data, but what else should I know?
```

---

📜 License
None

---
