// All API calls to the DriftWatch FastAPI backend.
// Base URL proxied through package.json → http://localhost:8000

const BASE = "/api/v1";

async function request(method, path, body) {
  const opts = {
    method,
    headers: { "Content-Type": "application/json" },
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(`${BASE}${path}`, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.detail || err.error || res.statusText);
  }
  return res.json();
}

export const api = {
  health:            ()         => request("GET",  "/health"),
  stats:             ()         => request("GET",  "/stats"),
  check:             (payload)  => request("POST", "/check",       payload),
  createFingerprint: (payload)  => request("POST", "/fingerprint", payload),
  getFingerprint:    (id)       => request("GET",  `/fingerprint/${id}`),
  listFingerprints:  ()         => request("GET",  "/fingerprints"),
  deleteFingerprint: (id)       => request("DELETE", `/fingerprint/${id}`),
  compare:           (payload)  => request("POST", "/compare",     payload),
  explain:           (payload)  => request("POST", "/explain",     payload),
};