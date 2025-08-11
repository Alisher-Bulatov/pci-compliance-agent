// webui/src/config.ts
// Normalise and harden the API base URL that Vite injects at *build time*.

const raw = String((import.meta as any)?.env?.VITE_API_BASE_URL ?? '').trim();

// If the env var is missing, fall back to localhost for dev.
// We also strip any trailing slashes so `${API_BASE}/path` never double-slashes.
export const API_BASE = (raw && raw !== 'undefined' ? raw : 'http://localhost:8000')
  .replace(/\/+$/, '');

// Helpful hint in the browser console so you can verify what the UI is using.
if (typeof window !== 'undefined') {
  // Don't spam production users; only log on non-production or if missing.
  const missing = !raw || raw === 'undefined';
  if (missing || /localhost|127\.0\.0\.1/.test(API_BASE)) {
    console.warn('[webui] API_BASE =', API_BASE, '(raw env =', raw || '<<missing>>', ')');
  }
}
