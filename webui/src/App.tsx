import { useState } from 'react';

type EventItem = {
  type: string;
  content?: string;
  result?: any;
  message?: string;
  detail?: string;
};

function App() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<EventItem[]>([]);
  const [loading, setLoading] = useState(false);

  const sendMessage = async () => {
    if (!input.trim()) return;

    setLoading(true);
    const response = await fetch('http://localhost:8000/ask_mock_full', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: input }),
    });

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    if (!reader) return;

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.trim()) {
          try {
            const item: EventItem = JSON.parse(line);
            setMessages((prev) => [...prev, item]);
          } catch (err) {
            console.error('Invalid JSON:', line);
          }
        }
      }
    }

    setLoading(false);
    setInput('');
  };

const renderItem = (item: EventItem, i: number) => {
  switch (item.type) {
    case 'message':
      return <div key={i}><strong>LLM:</strong> {item.content}</div>;
    case 'tool_result':
      return <pre key={i}>{JSON.stringify(item.result, null, 2)}</pre>;
    case 'stage':
    case 'info':
      return <div key={i} style={{ color: 'gray' }}>{item.message}</div>;
    case 'error':
      return <div key={i} style={{ color: 'red' }}>{item.detail || item.message}</div>;
    case 'token':
      return <span key={i}>{item.text}</span>;  // 👈 this handles streaming text
    default:
      return <div key={i} style={{ color: 'orange' }}>⚠ Unknown event: {item.type}</div>;
  }
};

  return (
    <div style={{ padding: '1rem', fontFamily: 'sans-serif' }}>
      <h2>🛡️ PCI DSS Compliance Agent (Mock Chat)</h2>
      <div style={{ marginBottom: '1rem' }}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
          style={{ width: '80%', padding: '0.5rem' }}
          placeholder="Ask something like: Compare 1.1.2 and 12.5.1"
        />
        <button onClick={sendMessage} disabled={loading} style={{ padding: '0.5rem' }}>
          {loading ? 'Loading...' : 'Send'}
        </button>
      </div>
      <div style={{ whiteSpace: 'pre-wrap' }}>
        {messages.map(renderItem)}
      </div>
    </div>
  );
}

export default App;
