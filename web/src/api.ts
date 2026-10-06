import type { AppState, ClosePreview } from "./types";

export class ApiError extends Error {
  allowed?: string;
  constructor(message: string, allowed?: string) {
    super(message);
    this.allowed = allowed;
  }
}

async function request<T>(method: "GET" | "POST", path: string, body?: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, {
      method,
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError("Can't reach Monay. Is it still running?");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof data.detail === "string" ? data.detail : "Something went wrong.";
    throw new ApiError(detail, data.allowed);
  }
  return data as T;
}

export const getState = () => request<AppState>("GET", "/api/state");
export const mutate = (path: string, body: unknown = {}) => request<AppState>("POST", path, body);
export const closePreview = () => request<ClosePreview>("GET", "/api/month/close-preview");
export const evaluate = (expr: string) =>
  request<{ value: string }>("POST", "/api/evaluate", { expr }).then((r) => r.value);
