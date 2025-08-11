// webui/src/App.tsx
import { useRef, useState } from "react";
import { API_BASE } from "./config";
import { askFull, askMockFull } from "./lib/api";

export default function App() {
  const [useLive, setUseLive] = useState(false);
  const [query, setQuery] = useState("");
  const [systemLog, setSystemLog] = useState<string[]>([]);
  const [clientLog, setClientLog] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  async function send(q?: string) {
    const message = (q ?? query).trim();
    if (!message || busy) return;

    setBusy(true);
    setSystemLog((l) => [...l, `Sending query: "${message}"`]);
    setClientLog([]);

    const payload = { message };

    try {
      const onLine = (obj: any) => {
        setClientLog((l) => [...l, JSON.stringify(obj)]);
      };
      if (useLive) {
        await askFull(payload, onLine);
      } else {
        await askMockFull(payload, onLine);
      }
    } catch (e: any) {
      setClientLog((l) => [...l, `Error: ${e?.message || e}`]);
    } finally {
      setBusy(false);
    }
  }

  function onKey(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") send();
  }

  return (
    <div style={{ minHeight: "100vh", background: "#1e1e1e", color: "#e5e7eb" }}>
      <div style={{ maxWidth: 980, margin: "0 auto", padding: "16px" }}>
        <header style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
          <div style={{ fontSize: 22, fontWeight: 700 }}>
            <span style={{ marginRight: 8 }}>🛡️</span> PCI DSS Compliance Agent (Mock Chat)
          </div>
          <div style={{ marginLeft: "auto", fontSize: 12, opacity: 0.8 }}>
            Backend: <code>{API_BASE}</code>
          </div>
        </header>

        <div style={{ fontSize: 12, marginBottom: 8 }}>
          <label style={{ display: "inline-flex", alignItems: "center", gap: 6, cursor: "pointer" }}>
            <input type="checkbox" checked={useLive} onChange={(e) => setUseLive(e.target.checked)} />
            Use Live Mode
          </label>
        </div>

        <div style={{ display: "flex", gap: 8 }}>
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onKey}
            placeholder="Ask something like: Compare 1.1.2 and 12.5.1"
            style={{
              flex: 1,
              background: "#111827",
              color: "#e5e7eb",
              border: "1px solid #374151",
              padding: "10px 12px",
              borderRadius: 6,
              outline: "none",
            }}
          />
          <button
            onClick={() => send()}
            disabled={busy}
            style={{
              background: busy ? "#374151" : "#2563eb",
              color: "#fff",
              border: 0,
              padding: "10px 14px",
              borderRadius: 6,
              cursor: busy ? "not-allowed" : "pointer",
              fontWeight: 600,
            }}
          >
            {busy ? "Sending…" : "Send"}
          </button>
        </div>

        <section style={{ marginTop: 18 }}>
          <div style={{ fontWeight: 600, marginBottom: 6 }}>System</div>
          <div
            style={{
              background: "#111827",
              border: "1px solid #374151",
              borderRadius: 8,
              padding: 12,
              minHeight: 84,
              whiteSpace: "pre-wrap",
              fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
              fontSize: 13,
            }}
          >
            {systemLog.length === 0 ? (
              <span style={{ opacity: 0.6 }}>Waiting…</span>
            ) : (
              systemLog.map((l, i) => <div key={i}>{l}</div>)
            )}
          </div>
        </section>

        <section style={{ marginTop: 18 }}>
          <div style={{ fontWeight: 600, marginBottom: 6 }}>Client</div>
          <div
            style={{
              background: "#111827",
              border: "1px solid #374151",
              borderRadius: 8,
              padding: 12,
              minHeight: 140,
              whiteSpace: "pre-wrap",
              fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
              fontSize: 13,
            }}
          >
            {clientLog.length === 0 ? (
              <span style={{ color: "#ef4444" }}>{busy ? "Streaming…" : "No output yet."}</span>
            ) : (
              clientLog.map((l, i) => <div key={i}>{l}</div>)
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
