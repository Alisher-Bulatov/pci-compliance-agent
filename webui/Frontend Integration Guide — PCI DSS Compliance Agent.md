
# Frontend Integration Guide — PCI DSS Compliance Agent

This guide explains how to integrate a React-based frontend with the FastAPI backend powering the PCI DSS Compliance Agent. The backend supports both live and mock endpoints for interactive and offline development.

## Backend Setup

Start the FastAPI server before using the frontend:

```bash
uvicorn mcp_server.main:app --reload
```

Default base URL: `http://localhost:8000`

## Available Endpoints

### 1. `/ask`

- **Method:** `GET`  
- **Type:** `text/event-stream`  
- **Use:** Raw LLM token stream  
- **Frontend Tool:** `EventSource`

```js
const source = new EventSource(`/ask?message=hello`);

source.onmessage = (event) => {
  console.log("Token:", event.data);
};
```

### 2. `/ask_full`

- **Method:** `POST`  
- **Type:** `application/x-ndjson`  
- **Use:** Structured stream (LLM + tools)  
- **Frontend Tool:** `fetch` + `ReadableStream`

```js
async function fetchFullResponse(message) {
  const response = await fetch("/ask_full", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ message }),
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    let lines = buffer.split("\n");
    buffer = lines.pop(); // preserve partial line

    for (const line of lines) {
      if (line.trim()) {
        const data = JSON.parse(line);
        console.log("Chunk:", data);
        // Render appropriately based on type
      }
    }
  }
}
```

### 3. `/ask_mock`

- **Method:** `GET`  
- **Type:** `text/event-stream`  
- **Use:** Mock version of `/ask` (for LLM simulation)

### 4. `/ask_mock_full`

- **Method:** `POST`  
- **Type:** `application/x-ndjson`  
- **Use:** Full structured mock stream (LLM + tools)  
- **Use this for UI prototyping without backend logic.**

```json
{"type": "tool_result", "result": "Mock comparison output"}
{"type": "message", "content": "This is a follow-up message."}
```

## Event Types (from CLI and API)

Each NDJSON line from `/ask_full` (or its mock) includes a `type` field:

| `type`       | Meaning                         | Example Use               |
|--------------|----------------------------------|---------------------------|
| `message`    | LLM reply or thought             | Show as chat bubble       |
| `tool_result`| Structured output from a tool    | Render as JSON view       |
| `token`      | LLM-generated token              | Animate in stream         |
| `stage`      | Processing stage info            | Display status label      |
| `info`       | Informational message            | Subtle UI update          |
| `error`      | Execution or validation error    | Display in alert style    |

### Suggested Renderer

```jsx
function renderItem(item) {
  switch (item.type) {
    case "message":
      return <p>{item.content}</p>;
    case "tool_result":
      return <pre>{JSON.stringify(item.result, null, 2)}</pre>;
    case "stage":
    case "info":
      return <div className="status">{item.message}</div>;
    case "error":
      return <p style={{ color: "red" }}>{item.detail}</p>;
    default:
      return null;
  }
}
```

## Development Tips

- Use `/ask_mock_full` to develop UI components offline  
- Simulate loading states, failures, and tool output  
- Build interfaces to handle multiple event types gracefully

## Cross-Origin Support

If your React dev server runs on a separate port (e.g., `http://localhost:3000`), enable CORS in `main.py`:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or restrict to ["http://localhost:3000"], use "*" only for local dev
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## CLI vs Web Interface

| Interface | File     | Description                     |
|-----------|----------|---------------------------------|
| CLI       | `cli.py` | Terminal-based chat client      |
| Web UI    | (TBD)    | React frontend with live stream |

## Endpoint Summary

| Endpoint          | Type                    | Requires LLM? | Description                    |
|-------------------|-------------------------|---------------|--------------------------------|
| `/ask`            | `text/event-stream`     | ✅            | Token-by-token LLM stream      |
| `/ask_full`       | `application/x-ndjson`  | ✅            | Full structured response       |
| `/ask_mock`       | `text/event-stream`     | ❌            | Simulated token stream         |
| `/ask_mock_full`  | `application/x-ndjson`  | ❌            | Simulated full agent response  |

## Final Integration Checklist

- [ ] Use `fetch` for `/ask_full` and parse NDJSON lines  
- [ ] Handle all known event `type`s gracefully  
- [ ] Use `EventSource` only for `/ask` or `/ask_mock`  
- [ ] Mock everything using `/ask_mock_full` when needed  
- [ ] Fallback gracefully on unknown types or JSON errors  
- [ ] Enable CORS for local frontend testing

