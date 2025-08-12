// webui/src/config.ts
// Single source of truth for the backend base URL.
// Vite reads variables prefixed with VITE_ at build time.
function stripTrailingSlash(s: string) {
  return s.replace(/\/+$/, "");
}

// 1) Env (preferred). Set at build time or in .env as VITE_API_BASE_URL.
const raw = (import.meta.env.VITE_API_BASE_URL ?? "").toString().trim();

// 2) URL override (?backend=https://host) for quick testing without rebuilding.
let urlOverride = "";
if (typeof window !== "undefined") {
  try {
    const u = new URL(window.location.href);
    urlOverride = u.searchParams.get("backend") ?? "";
  } catch {}
}

// 3) Fallback for local dev
let base = (urlOverride || raw || "http://localhost:8080").trim();
base = stripTrailingSlash(base);

// If the page is https and the API is http on the *same host*, upgrade scheme
try {
  if (typeof window !== "undefined") {
    const page = new URL(window.location.href);
    const api = new URL(base, page.href);
    if (page.protocol === "https:" && api.protocol === "http:" && page.hostname === api.hostname) {
      api.protocol = "https:";
      base = stripTrailingSlash(api.toString());
    }
  }
} catch {
  /* noop */
}

export const API_BASE = base;

// Debug hook for quick inspection in dev tools
if (typeof window !== "undefined") {
  (window as any).__API_BASE__ = API_BASE;
  if (!raw) {
    console.warn("[webui] VITE_API_BASE_URL not set at build. Using:", API_BASE);
  } else {
    console.info("[webui] API_BASE =", API_BASE);
  }
}
