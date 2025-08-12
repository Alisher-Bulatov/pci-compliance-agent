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

type Phase = "pre" | "tools" | "answer";
const PHASE: Record<Uppercase<Phase>, Phase> = { PRE: "pre", TOOLS: "tools", ANSWER: "answer" };

const NOISY_MATERIALS = [
  /^✅?\s*Done\b/i,
  /^Mock response completed\b/i,
  /^\s*Routing\b/i,
  /^\s*Running\b/i,
  /^\s*Reasoning based on tool results/i,
];

function isToolsStage(label: string) {
  return /Tools\b|Sending query|Tool|MCP|Routing|Running\b|compare_requirements|get\(|get:|search/i.test(label);
}
function isAnswerStage(label: string) {
  return /^Answer\b/i.test(label) || /Producing final answer|Reasoning based on/i.test(label);
}
function scrubMaterials(s: string) {
  const lines = s.split(/\r?\n/);
  const kept = lines.filter((ln) => !NOISY_MATERIALS.some((rx) => rx.test(ln.trim())));
  return kept.join("\n");
}

export default function App() {
  const [useLive, setUseLive] = useState(true);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const scrollerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollerRef.current?.scrollTo({ top: scrollerRef.current.scrollHeight, behavior: "smooth" });
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
        return;
      }

      // Segment-aware token routing
      if (e?.type === "token") {
        const { text = "", segment } = e as TokenEvent;

        setTurns((list) =>
          list.map((t) => {
            if (t.id !== id) return t;

            // 1) If segment present, trust it
            if (segment === "materials") return { ...t, materials: t.materials + text };
            if (segment === "answer")    return { ...t, answer: t.answer + text };

            // 2) Otherwise fall back to current phase
            if (phase === PHASE.ANSWER)  return { ...t, answer: t.answer + text };
            return { ...t, materials: t.materials + text };
          })
        );
        return;
      }

      if (e?.type === "info") {
        setTurns((list) =>
          list.map((t) =>
            t.id === id ? { ...t, meta: ((t.meta ?? "") + ((e as InfoEvent).message || "")).trim() } : t
          )
        );
        return;
      }

      if (e?.type === "error") {
        setTurns((list) =>
          list.map((t) =>
            t.id === id ? { ...t, error: (e as ErrorEvent).message ?? "Unknown error", done: true } : t
          )
        );
        setBusy(false);
        return;
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
        <div style={{ fontWeight: 700 }}>PCI DSS Compliance Agent (Mock Chat)</div>
        <div style={{ fontSize: 12, opacity: 0.7 }}>Backend: {API_BASE}</div>
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
          <label style={{ fontSize: 14, display: "flex", alignItems: "center", gap: 6, cursor: "pointer" }}>
            <input type="checkbox" checked={useLive} onChange={(e) => setUseLive(e.target.checked)} />
            Use Live Mode
          </label>
        </div>
      </div>
    ),
    [useLive]
  );

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column", background: "#0b0e14" }}>
      <div style={{ background: "#0f1420", color: "#eaeef7" }}>{header}</div>

      <div style={{ flex: 1, overflow: "auto", padding: 16 }}>
        {turns.map((t) => (
          <div key={t.id} style={{ display: "grid", gap: 8, margin: "10px auto 24px", maxWidth: 900 }}>
            {/* user bubble */}
            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <div
                style={{
                  background: "#1a2030",
                  color: "#cfe1ff",
                  padding: "10px 12px",
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
              <details style={{ background: "#0f1420", border: "1px solid #23314d", borderRadius: 10, padding: "8px 10px" }} open>
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
            disabled={busy || !input.trim()}
            style={{
              background: busy ? "#22304b" : "#3559e6",
              color: "white",
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
