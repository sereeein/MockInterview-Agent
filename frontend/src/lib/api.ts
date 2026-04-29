import type {
  DrillResponse,
  MockReport,
  MockSession,
  Question,
  ResumeUploadResponse,
  SingleReport,
} from "./types";
import { getActiveConfig } from "./provider-config";

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
  return true;
}

function providerHeaders(): Record<string, string> {
  const cfg = getActiveConfig();
  if (!cfg) return {};
  const h: Record<string, string> = {
    "X-Provider": cfg.provider,
    "X-API-Key": cfg.apiKey,
  };
  if (cfg.model) h["X-Model"] = cfg.model;
  if (cfg.baseUrl) h["X-Base-URL"] = cfg.baseUrl;
  return h;
}

function redirectToSetupOnAuthFailure(status: number): void {
  if (typeof window === "undefined") return;
  if (status === 401) {
    const next = window.location.pathname + window.location.search;
    window.location.href = `/setup?next=${encodeURIComponent(next)}`;
  }
}

async function jsonRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    ...(isJsonBody(init?.body) ? { "Content-Type": "application/json" } : {}),
    ...providerHeaders(),
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
    redirectToSetupOnAuthFailure(r.status);
    throw new ApiError(r.status, body);
  }
  return r.json() as Promise<T>;
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  return jsonRequest<T>(path, init);
}

export async function health(): Promise<{ status: string }> {
  return jsonRequest("/health");
}

export async function uploadResume(
  file: File,
  role_type: string,
  jd_text?: string,
  company_name?: string
): Promise<ResumeUploadResponse> {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("role_type", role_type);
  if (jd_text) fd.append("jd_text", jd_text);
  if (company_name) fd.append("company_name", company_name);
  const r = await fetch(`${BASE}/resume`, {
    method: "POST",
    body: fd,
    headers: providerHeaders(),
  });
  if (!r.ok) {
    let body: unknown;
    try {
      body = await r.json();
    } catch {
      body = await r.text();
    }
    redirectToSetupOnAuthFailure(r.status);
    throw new ApiError(r.status, body);
  }
  return r.json();
}

export async function generateQuestions(resume_session_id: number): Promise<Question[]> {
  return jsonRequest("/questions/generate", {
    method: "POST",
    body: JSON.stringify({ resume_session_id }),
  });
}

export async function listQuestions(
  resume_session_id: number,
  filters?: { category?: string; status?: string }
): Promise<Question[]> {
  const p = new URLSearchParams({ resume_session_id: String(resume_session_id) });
  if (filters?.category) p.set("category", filters.category);
  if (filters?.status) p.set("status", filters.status);
  return jsonRequest(`/questions?${p.toString()}`);
}

export async function startDrill(question_id: number): Promise<DrillResponse> {
  return jsonRequest("/drill", {
    method: "POST",
    body: JSON.stringify({ question_id }),
  });
}

export async function answerDrill(drill_id: number, text: string): Promise<DrillResponse> {
  return jsonRequest(`/drill/${drill_id}/answer`, {
    method: "POST",
    body: JSON.stringify({ text }),
  });
}

export async function getDrillReport(drill_id: number): Promise<SingleReport> {
  return jsonRequest(`/reports/drill/${drill_id}`);
}

export async function startMock(resume_session_id: number): Promise<MockSession> {
  return jsonRequest("/mock", {
    method: "POST",
    body: JSON.stringify({ resume_session_id }),
  });
}

export async function getMock(mock_id: number): Promise<MockSession> {
  return jsonRequest(`/mock/${mock_id}`);
}

export async function getMockReport(mock_id: number): Promise<MockReport> {
  return jsonRequest(`/reports/mock/${mock_id}`);
}
