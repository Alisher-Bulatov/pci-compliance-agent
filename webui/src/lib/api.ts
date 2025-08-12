// webui/src/lib/api.ts
import { API_BASE } from "../config";

function join(base: string, path: string) {
  return `${base.replace(/\/+$/, "")}/${path.replace(/^\/+/, "")}`;
}

export async function postNdjson<TReq extends object>(
  path: string,
  body: TReq,
  onLine: (obj: any) => void
) {
  const res = await fetch(join(API_BASE, path), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok || !res.body) {
    throw new Error(`HTTP ${res.status} when POST ${path}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });

    // NDJSON: split by newline, keep tail as partial
    const parts = buf.split("\n");
    buf = parts.pop() ?? "";

    for (const line of parts) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      try {
        onLine(JSON.parse(trimmed));
      } catch {
        // tolerate occasional partials or logs
      }
    }
  }
  // flush tail
  const tail = buf.trim();
  if (tail) {
    try {
      onLine(JSON.parse(tail));
    } catch {
      /* ignore */
    }
  }
}

// Convenience wrappers
export const askMockFull = (payload: any, onLine: (o: any) => void) =>
  postNdjson("/ask_mock_full", payload, onLine);

export const askFull = (payload: any, onLine: (o: any) => void) =>
  postNdjson("/ask_full", payload, onLine);
