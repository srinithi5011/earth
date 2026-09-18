import { useEffect, useState } from "react";

function generateSessionId(): string {
  return `session-${Math.random().toString(36).slice(2)}-${Date.now()}`;
}

export function useSessionId(): string {
  const [sessionId] = useState<string>(() => {
    const existing = window.sessionStorage.getItem("darukaa_session_id");
    if (existing) return existing;
    const fresh = generateSessionId();
    window.sessionStorage.setItem("darukaa_session_id", fresh);
    return fresh;
  });
  return sessionId;
}

export function useConversationId(): [string | null, (id: string) => void] {
  const [conversationId, setConversationIdState] = useState<string | null>(() =>
    window.sessionStorage.getItem("darukaa_conversation_id")
  );
  const setConversationId = (id: string) => {
    window.sessionStorage.setItem("darukaa_conversation_id", id);
    setConversationIdState(id);
  };
  return [conversationId, setConversationId];
}
