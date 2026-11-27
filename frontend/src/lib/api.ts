/** Typed API client — access token in memory only; refresh via HttpOnly cookie (ACC-15). */

export class ApiError extends Error {
  code: string;
  correlationId: string;
  status: number;
  details: Record<string, unknown>;
  constructor(status: number, code: string, message: string, correlationId: string, details: Record<string, unknown> = {}) {
    super(message);
    this.status = status;
    this.code = code;
    this.correlationId = correlationId;
    this.details = details;
  }
}

let accessToken: string | null = null;
export const setAccessToken = (t: string | null) => { accessToken = t; };
/** خواندن توکن جاری فقط برای پل‌های درون‌حافظه‌ای (مثل ویجت دستیار هوشمند — v1.6)؛ هرگز به localStorage نمی‌رود (ACC-15). */
export const getAccessToken = () => accessToken;

async function refreshOnce(): Promise<boolean> {
  const res = await fetch("/api/v1/auth/refresh", { method: "POST", credentials: "include" });
  if (!res.ok) return false;
  const data = await res.json();
  accessToken = data.access_token;
  return true;
}

export async function api<T = unknown>(path: string, options: RequestInit = {}, retry = true): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json", ...(options.headers as Record<string, string> | undefined) };
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
  const res = await fetch(`/api/v1${path}`, { ...options, headers, credentials: "include" });
  if (res.status === 401 && retry && !path.startsWith("/auth/login")) {
    const ok = await refreshOnce();
    if (ok) return api<T>(path, options, false);
  }
  if (!res.ok) {
    let body: { code?: string; message?: string; correlation_id?: string; details?: Record<string, unknown> } = {};
    try { body = await res.json(); } catch { /* non-JSON error */ }
    throw new ApiError(res.status, body.code ?? "HTTP_ERROR", body.message ?? "خطای ارتباط با سرور", body.correlation_id ?? "-", (body.details ?? {}) as Record<string, unknown>);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const get = <T = unknown>(p: string) => api<T>(p);
export const post = <T = unknown>(p: string, body?: unknown, idempotencyKey?: string) =>
  api<T>(p, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body),
    headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : {} });
export const patch = <T = unknown>(p: string, body?: unknown) => api<T>(p, { method: "PATCH", body: JSON.stringify(body ?? {}) });
export const put = <T = unknown>(p: string, body?: unknown) => api<T>(p, { method: "PUT", body: JSON.stringify(body ?? {}) });
