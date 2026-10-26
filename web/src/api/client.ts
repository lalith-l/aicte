/**
 * Fetch wrapper for AICTE Validator API.
 * All responses include synthetic_data: true.
 * Gracefully falls back to seeded data when API unavailable.
 */

export const API_BASE = import.meta.env.VITE_API_BASE ?? "";

export function getToken(): string | null {
  return localStorage.getItem("aicte_token");
}

export function setToken(token: string, role: string): void {
  localStorage.setItem("aicte_token", token);
  localStorage.setItem("aicte_role", role);
}

export function clearToken(): void {
  localStorage.removeItem("aicte_token");
  localStorage.removeItem("aicte_role");
}

export function getStoredRole(): string | null {
  return localStorage.getItem("aicte_role");
}

async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...((options.headers as Record<string, string>) || {}),
  };
  if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: "include",
    headers,
  });
  if (res.status === 401) {
    clearToken();
    window.location.hash = "#/login";
    throw new Error("Unauthorized");
  }
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`${res.status}: ${err}`);
  }
  return res.json();
}

export const api = {
  get: <T>(path: string) => apiFetch<T>(path),
  post: <T>(path: string, body: unknown) =>
    apiFetch<T>(path, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  put: <T>(path: string, body: unknown) =>
    apiFetch<T>(path, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  patch: <T>(path: string, body?: unknown) =>
    apiFetch<T>(path, {
      method: "PATCH",
      body: body ? JSON.stringify(body) : undefined,
    }),

  // Login
  login: (username: string, password: string) =>
    apiFetch<{ access_token: string; role: string }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),

  me: () =>
    apiFetch<{
      user_id: string;
      username: string;
      role: string;
      institution_id: string | null;
    }>("/api/auth/me"),
};
