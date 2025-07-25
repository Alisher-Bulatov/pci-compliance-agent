import './App.css';
import { useState, useEffect, useRef } from 'react';

type EventItem =
  | { type: 'token'; text: string }
  | { type: 'message'; content: string }
  | { type: 'tool_call'; tool_name: string; tool_input: Record<string, any> }
  | { type: 'tool_result'; text: any }
  | { type: 'info'; message: string }
  | { type: 'error'; message?: string; detail?: string }
  | { type: 'stage'; label: string }
  | { type: string; [key: string]: any };

type GroupedStage = {
  stage: string;
  items: EventItem[];
};

function App() {
  const [input, setInput] = useState('');
  const [groups, setGroups] = useState<GroupedStage[]>([]);
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<'mock' | 'live'>(
    () => (localStorage.getItem('chatMode') as 'mock' | 'live') || 'mock'
  );
  const [tokenBuffer, setTokenBuffer] = useState('');
  const controllerRef = useRef<AbortController | null>(null);

  const stopStream = () => {
    if (controllerRef.current) {
      controllerRef.current.abort();
      controllerRef.current = null;
      setLoading(false);
    }
  };
  const latestMessageRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    localStorage.setItem('chatMode', mode);
  }, [mode]);

  useEffect(() => {
    if (latestMessageRef.current) {
      latestMessageRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [groups, tokenBuffer]);

  const sendMessage = async () => {
    if (!input.trim()) return;

    let groupsCopy: GroupedStage[] = [
      {
        stage: 'System',
        items: [{ type: 'info', message: `Sending query: "${input}"` }]
      }
    ];
    setGroups(groupsCopy);
    setLoading(true);
    setTokenBuffer('');

    const endpoint =
      mode === 'live'
        ? 'http://localhost:8000/ask_full'
        : 'http://localhost:8000/ask_mock_full';

    const controller = new AbortController();
    controllerRef.current = controller;
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: input }),
      signal: controller.signal
    });

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let localTokenBuffer = '';

    if (!reader) {
      setLoading(false);
      setInput('');
      return;
    }

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (!line.trim()) continue;

        try {
          const item: EventItem = JSON.parse(line);
          if (item.type === 'token') {
            localTokenBuffer += item.text || '';
            continue;
          }

          if (item.type === 'stage') {
            if (localTokenBuffer.length > 0) {
              groupsCopy[groupsCopy.length - 1]?.items.push({
                type: 'message',
                content: localTokenBuffer
              });
              localTokenBuffer = '';
            }
            groupsCopy.push({ stage: item.label || item.message || 'Unnamed Stage', items: [] });
            continue;
          }

          if (localTokenBuffer.length > 0) {
            groupsCopy[groupsCopy.length - 1]?.items.push({
              type: 'message',
              content: localTokenBuffer
            });
            localTokenBuffer = '';
          }

          const currentGroup = groupsCopy[groupsCopy.length - 1];
          const isDuplicateTool =
            item.type === 'tool_result' &&
            currentGroup.items.some(
              (i) =>
                i.type === 'tool_result' &&
                JSON.stringify(i.text) === JSON.stringify(item.text)
            );

          if (!isDuplicateTool) {
            currentGroup.items.push(item);
          }
        } catch (err) {
          console.error('Invalid JSON:', line);
        }
      }

      setGroups([...groupsCopy]);
      setTokenBuffer(localTokenBuffer);
    }

    if (localTokenBuffer.length > 0) {
      groupsCopy[groupsCopy.length - 1]?.items.push({
        type: 'message',
        content: localTokenBuffer
      });
    }

    setGroups([...groupsCopy]);
    setTokenBuffer('');
    setLoading(false);
    setInput('');
  };

  const renderers: Record<string, (item: EventItem, i: number) => JSX.Element> = {
    message: (item, i) => <div key={i} className="fade-in">{item.content}</div>,
    tool_call: (item, i) => (
      <div key={i} className="tool-box tool-call fade-in">
        📦 <b>Tool Call:</b><br />
        <b>{item.tool_name}</b><br />
        {JSON.stringify(item.tool_input, null, 2)}
      </div>
    ),
    tool_result: (item, i) => (
      <div key={i} className="tool-box tool-result fade-in">
        📄 <b>Tool Result:</b><br />
        {typeof item.text === 'string'
          ? item.text
          : JSON.stringify(item.text, null, 2)}
      </div>
    ),
    info: (item, i) => <div key={i} className="info fade-in">{item.message}</div>,
    error: (item, i) => <div key={i} className="error fade-in">Error: {item.detail || item.message}</div>,
    stage: () => <></>
  };

  return (
    <div className="app-container">
      <h2>🛡️ PCI DSS Compliance Agent ({mode === 'live' ? 'Live' : 'Mock'} Chat)</h2>

      <div style={{ marginBottom: '1rem' }}>
        <label>
          <input
            type="checkbox"
            checked={mode === 'live'}
            onChange={() => setMode(mode === 'live' ? 'mock' : 'live')}
          />{' '}
          Use Live Mode
        </label>
      </div>

      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
        <input
          className="chat-input"
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
          placeholder="Ask something like: Compare 1.1.2 and 12.5.1"
        />
        
{!loading ? (
  
<button
  className={"chat-button" + (loading ? " stop" : "")}
  onClick={loading ? stopStream : sendMessage}
  title={loading ? "Stop streaming" : "Send message"}
  disabled={loading && false}  // keep button enabled for stopping
>
  {loading ? (
    <>
      ⏹ Streaming<span className="dot-pulse" />
    </>
  ) : (
    <>
      ▶ Send
    </>
  )}
</button>


) : (
  <>
    <button className="chat-button" disabled>
      Responding...
    </button>
    <button
      className="chat-button stop"
      onClick={stopStream}
      title="Stop response"
    >
      ⏹ Stop<span className="dot-pulse" />
    </button>
  </>
)}

      </div>

      <div>
        {groups.map((group, gi) => (
          <div key={gi} className="stage-block">
            <div style={{ fontWeight: 'bold', fontSize: '1.1em', color: '#8bc4ff', marginBottom: '0.5em' }}>
              {group.stage}
            </div>
            {group.items.map((item, i) =>
              renderers[item.type]?.(item, i) ?? (
                <div key={i} className="fade-in" style={{ color: 'orange' }}>
                  ⚠ Unknown event: {item.type}
                </div>
              )
            )}
            {gi === groups.length - 1 && tokenBuffer && (
              <div ref={latestMessageRef} className="fade-in" style={{ color: '#aaa', fontStyle: 'italic' }}>
                {tokenBuffer}
                <span className="cursor">▌</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default App;
