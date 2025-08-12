// webui/src/App.tsx
import { useRef, useState } from "react";
import { API_BASE } from "./config";
import { askFull, askMockFull } from "./lib/api";

type EventLine =
  | { type: "token"; text: string }
  | { type: "stage"; label: string }
  | { type: "info"; message: string }
  | { type: "error"; message: string }
  | Record<string, unknown>;

const BUILD_TAG = "ui-0812g";

export default function App() {
  const [useLive, setUseLive] = useState(false);
  const [query, setQuery] = useState("");
  const [systemLog, setSystemLog] = useState<string[]>([]);
  const [answer, setAnswer] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function reset() {
    setSystemLog([]);
    setAnswer("");
    setQuery("");
    inputRef.current?.focus();
  }

  function handleLine(obj: EventLine) {
    if (!obj || typeof obj !== "object") return;

    if ((obj as any).type === "stage") {
      setSystemLog((l) => [...l, String((obj as any).label || "")]);
      return;
    }
    if ((obj as any).type === "info") {
      setSystemLog((l) => [...l, `ℹ️ ${(obj as any).message || ""}`]);
      return;
    }
    if ((obj as any).type === "error") {
      setSystemLog((l) => [...l, `❌ ${(obj as any).message || ""}`]);
      return;
    }
    if ((obj as any).type === "token") {
      setAnswer((s) => s + String((obj as any).text || ""));
      return;
    }
    // Fallback: dump unknown events into system log for debugging
    setSystemLog((l) => [...l, JSON.stringify(obj)]);
  }

  async function send(q?: string) {
    const message = (q ?? query).trim();
    if (!message || busy) return;

    setBusy(true);
    setSystemLog((l) => [...l, `Sending query: "${message}"`]);
    setAnswer("");

    const payload = { message };

    try {
      const onLine = (obj: any) => handleLine(obj);
      if (useLive) {
        await askFull(payload, onLine);
      } else {
        await askMockFull(payload, onLine);
      }
      setSystemLog((l) => [...l, "✅ Done"]);
    } catch (e: any) {
      setSystemLog((l) => [...l, `❌ Request failed: ${e?.message || e}`]);
    } finally {
      setBusy(false);
      inputRef.current?.focus();
    }
  }

  function onKey(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") send();
  }

  return (
    <div style={{ minHeight: "100vh", background: "#0f172a", color: "#e5e7eb" }}>
      <div style={{ maxWidth: 980, margin: "0 auto", padding: 16 }}>
        <header style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12, flexWrap: "wrap" }}>
          <div style={{ fontSize: 20, fontWeight: 700 }}>
            <span style={{ marginRight: 8 }}>🛡️</span> PCI DSS Compliance Agent (Mock Chat)
          </div>
          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 10 }}>
            <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
              <input type="checkbox" checked={useLive} onChange={(e) => setUseLive(e.target.checked)} />
              <span>Use Live Mode</span>
            </label>
          </div>
        </header>

        <div style={{ fontSize: 12, opacity: 0.85, marginBottom: 8 }}>
          Backend: <code>{API_BASE}</code> · Build: <code>{BUILD_TAG}</code>
        </div>

        <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
          <input
            ref={inputRef}
            placeholder='Ask something… e.g., "Is 3.2.1 focused on storage vs transmission?"'
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onKey}
            disabled={busy}
            style={{
              flex: 1,
              background: "#111827",
              color: "#e5e7eb",
              border: "1px solid #374151",
              borderRadius: 10,
              padding: "12px 14px",
              outline: "none",
            }}
          />
          <button
            onClick={() => send()}
            disabled={busy || !query.trim()}
            style={{
              background: busy ? "#334155" : "#6366f1",
              color: "white",
              border: 0,
              borderRadius: 10,
              padding: "10px 14px",
              fontWeight: 600,
              cursor: busy ? "not-allowed" : "pointer",
              minWidth: 88,
            }}
          >
            {busy ? "Sending…" : "Send"}
          </button>
          <button
            onClick={reset}
            disabled={busy}
            style={{
              background: "#0b1220",
              color: "#cbd5e1",
              border: "1px solid #334155",
              borderRadius: 10,
              padding: "10px 14px",
              cursor: busy ? "not-allowed" : "pointer",
            }}
          >
            Reset
          </button>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <section>
            <div style={{ fontWeight: 700, marginBottom: 8 }}>System</div>
            <div
              style={{
                background: "#0b1220",
                border: "1px solid #1f2937",
                borderRadius: 12,
                padding: 12,
                minHeight: 220,
                whiteSpace: "pre-wrap",
                fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                fontSize: 13,
              }}
            >
              {systemLog.length === 0 ? (
                <span style={{ color: "#94a3b8" }}>{busy ? "Streaming…" : "Nothing yet."}</span>
              ) : (
                systemLog.map((l, i) => <div key={i}>{l}</div>)
              )}
            </div>
          </section>

          <section>
            <div style={{ fontWeight: 700, marginBottom: 8 }}>Client</div>
            <div
              style={{
                background: "#0b1220",
                border: "1px solid #1f2937",
                borderRadius: 12,
                padding: 12,
                minHeight: 220,
                whiteSpace: "pre-wrap",
                fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                fontSize: 15,
                lineHeight: 1.5,
              }}
            >
              {answer ? <>{answer}</> : <span style={{ color: "#ef4444" }}>{busy ? "Streaming…" : "No output yet."}</span>}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
