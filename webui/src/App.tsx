import { useState, useEffect } from 'react';

type EventItem =
  | { type: 'token'; text: string }
  | { type: 'message'; content: string }
  | { type: 'tool_call'; tool_name: string; tool_input: Record<string, any> }
  | { type: 'tool_result'; result: any }
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

  useEffect(() => {
    localStorage.setItem('chatMode', mode);
  }, [mode]);

const sendMessage = async () => {
  if (!input.trim()) return;

  // Initialize with the system message
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

  const response = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: input })
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
        console.log('[event]', item);

        if (item.type === 'token') {
          localTokenBuffer += item.text || '';
          continue;
        }

        // If a new stage arrives, flush any token text as a message first
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

        // If there's any buffered token text, add it before the next message
        if (localTokenBuffer.length > 0) {
          groupsCopy[groupsCopy.length - 1]?.items.push({
            type: 'message',
            content: localTokenBuffer
          });
          localTokenBuffer = '';
        }

        const currentGroup = groupsCopy[groupsCopy.length - 1];
        if (!currentGroup) {
          groupsCopy.push({ stage: 'Ungrouped', items: [item] });
        } else {
          const isDuplicateTool =
            item.type === 'tool_result' &&
            currentGroup.items.some(
              (i) =>
                i.type === 'tool_result' &&
                JSON.stringify(i.result) === JSON.stringify(item.text)
            );

          if (!isDuplicateTool) {
            currentGroup.items.push(item);
          }
        }
      } catch (err) {
        console.error('Invalid JSON:', line);
      }
    }

    // Update React state once per read chunk
    setGroups([...groupsCopy]);
    setTokenBuffer(localTokenBuffer); // So user sees streaming text
  }

  // Flush any remaining buffer after final read
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
    message: (item, i) => <div key={i} style={{ marginBottom: '0.5em' }}>{item.content}</div>,
    tool_call: (item, i) => (
      <div
        key={i}
        style={{
          fontFamily: 'monospace',
          whiteSpace: 'pre-wrap',
          color: '#9ec7ff',
          background: '#111',
          padding: '0.75em',
          borderRadius: 4,
          marginBottom: '0.5em'
        }}
      >
        📦 <b>Tool Call:</b><br />
        <b>{item.tool_name}</b><br />
        {JSON.stringify(item.tool_input, null, 2)}
      </div>
    ),
    tool_result: (item, i) => (
      <div
        key={i}
        style={{
          fontFamily: 'monospace',
          whiteSpace: 'pre-wrap',
          background: '#1c1c1c',
          color: '#abf7b1',
          padding: '0.75em',
          borderRadius: 4,
          marginBottom: '0.5em'
        }}
      >
        📄 <b>Tool Result:</b><br />
        {JSON.stringify(item.text, null, 2)}
      </div>
    ),
    info: (item, i) => (
      <div key={i} style={{ color: 'gray', fontStyle: 'italic' }}>{item.message}</div>
    ),
    error: (item, i) => (
      <div key={i} style={{ color: 'red' }}>
        Error: {item.detail || item.message}
      </div>
    ),
    stage: () => <></>
  };

  return (
    <div style={{ padding: '1rem', fontFamily: 'sans-serif', color: '#f0f0f0', background: '#181818', minHeight: '100vh' }}>
      <h2 style={{ color: '#6ec1ff' }}>🛡️ PCI DSS Compliance Agent ({mode === 'live' ? 'Live' : 'Mock'} Chat)</h2>

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
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
          placeholder="Ask something like: Compare 1.1.2 and 12.5.1"
          style={{
            flexGrow: 1,
            padding: '0.5rem',
            background: '#222',
            color: 'white',
            border: '1px solid #333'
          }}
        />
        <button onClick={sendMessage} disabled={loading} style={{ padding: '0.5rem 1rem' }}>
          {loading ? '...' : 'Send'}
        </button>
      </div>

      <div>
        {groups.map((group, gi) => (
          <div key={gi} style={{ marginBottom: '2em' }}>
            <div style={{ fontWeight: 'bold', fontSize: '1.1em', color: '#8bc4ff', marginBottom: '0.5em' }}>
              {group.stage}
            </div>
            {group.items.map((item, i) =>
              renderers[item.type]?.(item, i) ?? (
                <div key={i} style={{ color: 'orange' }}>
                  ⚠ Unknown event: {item.type}
                </div>
              )
            )}
            {gi === groups.length - 1 && tokenBuffer && (
              <div style={{ color: '#aaa', fontStyle: 'italic' }}>
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
