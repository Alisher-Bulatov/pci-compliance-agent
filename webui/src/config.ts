// webui/src/config.ts
// Resolve API base for both dev and production builds (Vite inlines at build time).

function stripTrailingSlash(s: string) {
  return s.replace(/\/+$/, "");
}

const raw = String((import.meta as any)?.env?.VITE_API_BASE_URL ?? "").trim();

// Dev fallback only if the env var isn't provided at build time.
let base = raw && raw !== "undefined" ? raw : "http://localhost:8000";
base = stripTrailingSlash(base);

// If the site is HTTPS but base is HTTP, upgrade the scheme to avoid mixed-content blocks.
try {
  if (typeof window !== "undefined") {
    const u = new URL(base, window.location.origin);
    if (window.location.protocol === "https:" && u.protocol === "http:") {
      base = "https://" + u.host + stripTrailingSlash(u.pathname);
    }
  }
} catch {
  // keep base as-is if URL parsing fails
}

export const API_BASE = base;

// Expose for quick verification in the browser console
if (typeof window !== "undefined") {
  (window as any).__API_BASE__ = API_BASE;
  const missing = !raw || raw === "undefined";
  if (missing) {
    console.warn("[webui] VITE_API_BASE_URL was missing at build time. Using:", API_BASE);
  } else {
    console.info("[webui] API_BASE =", API_BASE);
  }
}
