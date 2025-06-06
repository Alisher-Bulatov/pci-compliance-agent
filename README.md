# PCI DSS Compliance Agent

This project is a document-aware assistant to help with PCI DSS compliance.

It uses a Retrieval-Augmented Generation (RAG) pipeline powered by FAISS to locate relevant PCI DSS content and combines it with LLM-generated reasoning. Tool calls (e.g., for retrieving requirement text) are executed via an MCP Server, making the system modular and extensible.

---

## 🔧 Key Components

- **FAISS Retriever**: Loads `pci_chunks.txt` and builds a searchable index.
- **LLM Agent**: Uses prompt formatting to trigger tool calls where needed.
- **MCP Server**: Executes tools like `get_requirement_text` via FastAPI.
- **CLI Interface**: Chat with the agent from terminal using `cli.py`.

---

## 🚀 How to Run

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Build the FAISS index:
   ```bash
   python scripts/build_index.py
   ```

3. Start the MCP server:
   ```bash
   uvicorn mcp_server.main:app --reload
   ```

4. In a separate terminal, start the CLI interface:
   ```bash
   python cli.py
   ```

5. Type `exit` or `quit` to end the session.

---

## 🧠 Assistant Capabilities

The agent can:

- Retrieve requirement text by ID
- Search for relevant topics (e.g., firewalls, encryption)
- Compare requirements side by side
- Recommend tools when user intent is ambiguous

All logic is tool-call driven and modular.

### ✅ Supported Tools

| Tool | Description |
|------|-------------|
| `get_requirement_text` | Retrieve the exact text of a specific requirement |
| `search_by_topic` | Retrieve relevant requirements based on a topic |
| `compare_requirements` | Compare full text of two or more requirements |
| `recommend_tool` | Suggest the best tool based on vague input |

---

## 🔍 Sample Prompts

Try interacting with the agent using:

```text
hello
What does 3.2.1 say?
Compare 1.1.2 and 12.5.1
Search for firewall rules
What are some encryption requirements?
```

---

## 📁 Project Structure

```text
.
├── cli.py                      # CLI interface entry point
├── mcp_server/
│   └── main.py                 # MCP server with FastAPI tools
├── tools/                      # Tool logic for requirement analysis
├── agent/
│   ├── prompt_template.txt
│   ├── followup_template.txt
│   ├── llm_wrapper.py
│   ├── prompt_formatter.py
│   └── tool_call_parser.py
├── retrieval/
│   ├── retriever.py
│   └── data/
│       ├── pci_index.faiss
│       └── mapping.pkl
├── scripts/
│   └── build_index.py
```

---

## 🧪 Debugging Tips

- `Parsed TOOL_CALL:` — agent is making an API call.
- `→ Tool Result:` — shows the tool response.
- `=== Follow-up from LLM ===` — explanation from the assistant.

---

## 📜 License

None