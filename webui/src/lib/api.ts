// webui/src/lib/api.ts
import { API_BASE } from "../config";

function join(base: string, path: string) {
  return `${base.replace(/\/+$/, "")}/${path.replace(/^\/+/, "")}`;
}

export async function postJson<TReq extends object, TRes = unknown>(
  path: string,
  body: TReq,
  init?: RequestInit
): Promise<TRes> {
  const res = await fetch(join(API_BASE, path), {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    body: JSON.stringify(body),
    ...init,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status} ${res.statusText}${text ? ` — ${text}` : ""}`);
  }
  return res.json() as Promise<TRes>;
}

/** NDJSON streaming helper for /ask_* endpoints */
export async function postNdjson<TReq extends object>(
  path: string,
  body: TReq,
  onLine: (obj: any) => void
): Promise<void> {
  const res = await fetch(join(API_BASE, path), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText}`);

  const reader = res.body?.getReader();
  if (!reader) return;

  const decoder = new TextDecoder();
  let buf = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });

    let idx: number;
    while ((idx = buf.indexOf("\n")) !== -1) {
      const line = buf.slice(0, idx).trim();
      buf = buf.slice(idx + 1);
      if (!line) continue;
      try { onLine(JSON.parse(line)); } catch { /* ignore partials */ }
    }
  }
  const tail = buf.trim();
  if (tail) { try { onLine(JSON.parse(tail)); } catch {} }
}

// Route conveniences
export const askMockFull = (payload: any, onLine: (o: any) => void) =>
  postNdjson("/ask_mock_full", payload, onLine);

export const askFull = (payload: any, onLine: (o: any) => void) =>
  postNdjson("/ask_full", payload, onLine);
