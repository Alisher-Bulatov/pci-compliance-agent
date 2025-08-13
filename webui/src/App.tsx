import { useEffect, useMemo, useRef, useState } from "react";
import { askFull, askMockFull } from "./lib/api";
import { API_BASE } from "./config";

type StageEvent = { type: "stage"; label: string };
type TokenEvent = { type: "token"; text: string; segment?: "materials" | "answer" };
type InfoEvent  = { type: "info"; message: string };
type ErrorEvent = { type: "error"; stage?: string; message: string };
type EventLine  = StageEvent | TokenEvent | InfoEvent | ErrorEvent | Record<string, unknown>;

type ChatTurn = {
  id: string;
  question: string;
  materials: string; // tool requests + tool results
  answer: string;    // reasoning/final answer
  done: boolean;
  error?: string;
  meta?: string;
};

const PHASE = {
  PRE: "pre",
  TOOLS: "tools",
  ANSWER: "answer",
} as const;
type Phase = (typeof PHASE)[keyof typeof PHASE];

const isToolsStage  = (s: string) => /^tools/i.test(s);
const isAnswerStage = (s: string) => /^answer/i.test(s);

function scrubMaterials(s: string): string {
  // Light cleanup for display
  return s
    .replace(/\r\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n");
}

export default function App() {
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [input, setInput]   = useState("");
  const [busy, setBusy]     = useState(false);
  const [useLive, setUseLive] = useState(true);

  const bottomRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns, busy]);

  const startAsk = async (question: string) => {
    const id = String(Date.now());
    const next: ChatTurn = { id, question, materials: "", answer: "", done: false };
    setTurns((t) => [...t, next]);
    setBusy(true);

    let phase: Phase = PHASE.PRE;

    const onLine = (e: EventLine) => {
      // Stage changes
      if (e?.type === "stage") {
        const label = ((e as StageEvent).label || "").trim();
        if (isToolsStage(label) && phase !== PHASE.ANSWER) {
          phase = PHASE.TOOLS;
          return;
        }
        if (isAnswerStage(label)) {
          phase = PHASE.ANSWER;
          return;
        }
      }

      // Info/meta
      if (e?.type === "info") {
        setTurns((list) =>
          list.map((t) =>
            t.id === id
              ? { ...t, meta: ((t.meta ?? "") + ((e as InfoEvent).message || "") + "\n").trim() }
              : t
          )
        );
        return;
      }

      // Error
      if (e?.type === "error") {
        const err = e as ErrorEvent;
        setTurns((list) =>
          list.map((t) =>
            t.id === id ? { ...t, error: err?.message ?? "Unknown error", done: true } : t
          )
        );
        setBusy(false);
        return;
      }

      // Token stream
      if ((e as TokenEvent)?.type === "token") {
        const { text = "", segment } = e as TokenEvent;

        // Route by segment when provided (trust it)
        if (segment === "materials") {
          setTurns((list) =>
            list.map((t) =>
              t.id === id ? { ...t, materials: t.materials + text } : t
            )
          );
          return;
        }
        if (segment === "answer") {
          setTurns((list) =>
            list.map((t) =>
              t.id === id ? { ...t, answer: t.answer + text } : t
            )
          );
          return;
        }

        // Otherwise fall back to current phase
        setTurns((list) =>
          list.map((t) => {
            if (t.id !== id) return t;
            if (phase === PHASE.ANSWER)  return { ...t, answer: t.answer + text };
            return { ...t, materials: t.materials + text };
          })
        );
        return;
      }

      // Unknown event line: show in meta
      try {
        const show = JSON.stringify(e);
        setTurns((list) =>
          list.map((t) =>
            t.id === id
              ? { ...t, meta: ((t.meta ?? "") + show + "\n").trim() }
              : t
          )
        );
      } catch {
        // ignore
      }
    };

    try {
      const ask = useLive ? askFull : askMockFull;
      await ask({ message: question }, onLine);

      setTurns((list) =>
        list.map((t) =>
          t.id === id
            ? {
                ...t,
                materials: scrubMaterials(t.materials.trim()),
                answer: t.answer.trim(),
                done: true,
              }
            : t
        )
      );
    } catch (err: any) {
      setTurns((list) =>
        list.map((t) => (t.id === id ? { ...t, error: err?.message ?? String(err), done: true } : t))
      );
    } finally {
      setBusy(false);
    }
  };

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const q = input.trim();
    if (!q || busy) return;
    setInput("");
    startAsk(q);
  };

  const header = useMemo(
    () => (
      <div style={{ display: "flex", gap: 12, alignItems: "center", padding: "8px 12px", borderBottom: "1px solid #1b2438" }}>
        <div style={{ fontWeight: 700 }}>PCI DSS Compliance Agent</div>
        <div style={{ fontSize: 12, opacity: 0.7 }}>Backend: {API_BASE}</div>
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
          <label style={{ fontSize: 14, display: "flex", alignItems: "center", gap: 6 }}>
            <input
              type="checkbox"
              checked={useLive}
              onChange={(e) => setUseLive(e.target.checked)}
            />
            Live backend
          </label>
        </div>
      </div>
    ),
    [useLive]
  );

  return (
    <div style={{ color: "#eaeef7", background: "#0b0e14", minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      {header}

      {/* Chat area */}
      <div style={{ flex: 1, overflowY: "auto", padding: 12 }}>
        {turns.map((t) => (
          <div key={t.id} style={{ display: "flex", flexDirection: "column", gap: 12, margin: "10px auto", maxWidth: 900 }}>
            {/* user bubble */}
            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <div
                style={{
                  background: "#1b2438",
                  color: "#f4f7ff",
                  padding: "12px 14px",
                  borderRadius: 12,
                  borderTopRightRadius: 4,
                  maxWidth: "80%",
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-word",
                }}
              >
                {t.question}
              </div>
            </div>

            {/* Retrieved materials */}
            {!!t.materials && (
              <details style={{ background: "#0f1420", border: "1px solid #23314d", borderRadius: 10, padding: "8px 10px" }}>
                <summary style={{ color: "#9fb5dd", cursor: "pointer", fontWeight: 600 }}>Retrieved materials</summary>
                <div
                  style={{
                    color: "#c6d4ef",
                    marginTop: 8,
                    background: "#0b0e14",
                    border: "1px solid #1e2a44",
                    borderRadius: 8,
                    padding: "8px 10px",
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                    fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
                    fontSize: 13,
                  }}
                >
                  {t.materials}
                </div>
              </details>
            )}

            {/* assistant bubble */}
            <div style={{ display: "flex", justifyContent: "flex-start" }}>
              <div
                style={{
                  background: "#111826",
                  color: "#f4f7ff",
                  padding: "12px 14px",
                  borderRadius: 12,
                  borderTopLeftRadius: 4,
                  maxWidth: "80%",
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-word",
                }}
              >
                {t.error ? `❌ ${t.error}` : t.answer || (t.done ? "…" : "Thinking…")}
              </div>
            </div>

            {!!t.meta && <div style={{ color: "#8ea5c9", fontSize: 12, marginLeft: 6 }}>ⓘ {t.meta}</div>}
          </div>
        ))}

        {busy && <div style={{ color: "#9fb5dd", textAlign: "center", padding: 8, opacity: 0.8 }}>Streaming…</div>}
        <div ref={bottomRef} />
      </div>

      {/* Composer */}
      <form onSubmit={onSubmit} style={{ padding: 12, borderTop: "1px solid #131a28", background: "#0f1420" }}>
        <div style={{ display: "flex", gap: 8, maxWidth: 900, margin: "0 auto" }}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a PCI DSS question…"
            disabled={busy}
            style={{
              flex: 1,
              background: "#0b0e14",
              color: "#eaeef7",
              border: "1px solid #1e2a44",
              borderRadius: 8,
              padding: "10px 12px",
              outline: "none",
            }}
          />
          <button
            type="submit"
            disabled={busy}
            style={{
              background: busy ? "#1b2438" : "#23314d",
              color: "#eaeef7",
              border: "none",
              borderRadius: 8,
              padding: "10px 14px",
              cursor: busy ? "not-allowed" : "pointer",
              fontWeight: 600,
            }}
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );
}
