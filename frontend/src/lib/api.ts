const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, body: unknown) {
    super(`${status} ${typeof body === "string" ? body : JSON.stringify(body)}`);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

function isJsonBody(body: BodyInit | null | undefined): boolean {
  if (body === undefined || body === null) return false;
  if (body instanceof FormData) return false;
  if (body instanceof Blob) return false;
  if (body instanceof URLSearchParams) return false;
  if (body instanceof ArrayBuffer) return false;
  return true; // string body — assume JSON
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    ...(isJsonBody(init?.body) ? { "Content-Type": "application/json" } : {}),
    ...((init?.headers as Record<string, string>) ?? {}),
  };
  const r = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!r.ok) {
    let body: unknown;
    try {
      body = await r.json();
    } catch {
      body = await r.text();
    }
    throw new ApiError(r.status, body);
  }
  return r.json() as Promise<T>;
}

export async function health(): Promise<{ status: string }> {
  return api("/health");
}
