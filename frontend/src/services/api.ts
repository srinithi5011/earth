import type { ChatResponse } from "../types";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* ignore parse failure */
    }
    throw new Error(`API error (${res.status}): ${detail}`);
  }
  return res.json();
}

export function getHealth() {
  return request<{
    status: string;
    demo_mode: boolean;
    database_ok: boolean;
    vector_backend: string;
  }>("/api/health");
}

export function sendChatMessage(params: {
  session_id: string;
  conversation_id?: string;
  message: string;
  structured_input?: Record<string, any>;
}) {
  return request<ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export function getConversation(conversationId: string) {
  return request<any>(`/api/conversations/${conversationId}`);
}

export function getEvidence(params?: { topic?: string; region?: string; organization?: string }) {
  const qs = new URLSearchParams(params as Record<string, string>).toString();
  return request<any[]>(`/api/evidence${qs ? `?${qs}` : ""}`);
}

export function getDocuments() {
  return request<any[]>("/api/evidence/documents");
}

export function getRelationships() {
  return request<any[]>("/api/relationships");
}

export { API_URL };
