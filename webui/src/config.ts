// single source of truth for the backend base URL.

function stripTrailingSlash(s: string) {
  return s.replace(/\/+$/, "");
}

// Read Vite env baked at build time (Amplify: VITE_API_BASE_URL)
// Use the exact literal so Vite replaces it at build time
const raw = (import.meta.env.VITE_API_BASE_URL ?? "").toString().trim();

// Dev fallback only if not set at build time
let base = raw && raw !== "undefined" ? raw : "http://localhost:8000";
base = stripTrailingSlash(base);

// If site is HTTPS and base is HTTP, upgrade scheme to avoid mixed content
try {
  if (typeof window !== "undefined") {
    const u = new URL(base, window.location.origin);
    if (window.location.protocol === "https:" && u.protocol === "http:") {
      base = "https:" + u.host + stripTrailingSlash(u.pathname);
    }
  }
} catch {
  /* keep base as-is */
}

export const API_BASE = base;

// Debug hook: check from console (`__API_BASE__`)
if (typeof window !== "undefined") {
  (window as any).__API_BASE__ = API_BASE;
  if (!raw || raw === "undefined") {
    console.warn("[webui] VITE_API_BASE_URL missing at build; using", API_BASE);
  } else {
    console.info("[webui] API_BASE =", API_BASE);
  }
}
