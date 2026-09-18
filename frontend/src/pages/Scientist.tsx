import React, { useEffect, useRef, useState } from "react";
import { useConversationId, useSessionId } from "../hooks/useSession";
import { sendChatMessage } from "../services/api";
import type { ChatMessage, ChatResponse, Recommendation } from "../types";

const INITIAL_ASSISTANT_MSG: ChatMessage = {
  role: "assistant",
  content:
    "I'm the Darukaa Earth AI Environmental Scientist. Describe your land — e.g. " +
    '"Biodiversity is declining on my farm" or give specifics like soil organic carbon, ' +
    "rainfall, crop, and region — and I'll ask for whatever's missing before assessing it.",
};

function RecommendationCard({ rec }: { rec: Recommendation }) {
  return (
    <div className="bg-emerald-50/80 border border-emerald-200/80 p-3.5 rounded-xl text-xs shadow-2xs hover:border-emerald-300 transition-colors">
      <div className="flex items-center justify-between font-bold text-emerald-950">
        <span className="text-xs">{rec.recommendation}</span>
        <span className="text-[10px] bg-emerald-100 text-emerald-900 px-2.5 py-0.5 rounded-full font-bold border border-emerald-300/60 shrink-0">
          {rec.confidence_label} ({Math.round(rec.confidence * 100)}%)
        </span>
      </div>
      <p className="text-slate-700 mt-1.5 leading-relaxed text-xs">
        {rec.scientific_reasoning}
      </p>
      {rec.affected_metrics && rec.affected_metrics.length > 0 && (
        <div className="mt-2.5 flex flex-wrap gap-1.5">
          {rec.affected_metrics.map((m, idx) => (
            <span
              key={idx}
              className="bg-white border border-emerald-200/80 text-emerald-900 text-[10px] px-2 py-0.5 rounded-md font-medium shadow-2xs"
            >
              {m}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Scientist() {
  const sessionId = useSessionId();
  const [conversationId, setConversationId] = useConversationId();

  // Load initial chat history from sessionStorage or fallback to default message
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    try {
      const saved = window.sessionStorage.getItem("darukaa_chat_history");
      return saved ? JSON.parse(saved) : [INITIAL_ASSISTANT_MSG];
    } catch {
      return [INITIAL_ASSISTANT_MSG];
    }
  });

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [showMetrics, setShowMetrics] = useState(false);
  const [soilCarbon, setSoilCarbon] = useState<string>("");
  const [rainfall, setRainfall] = useState<string>("");
  const [region, setRegion] = useState<string>("");

  const scrollRef = useRef<HTMLDivElement>(null);
  const activeMetricsCount = [soilCarbon, rainfall, region].filter(Boolean).length;

  // Sync messages to sessionStorage whenever they update
  useEffect(() => {
    try {
      window.sessionStorage.setItem("darukaa_chat_history", JSON.stringify(messages));
    } catch {
      // Ignore storage write issues
    }
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, loading]);

  async function handleSend() {
    const text = input.trim();
    if ((!text && !soilCarbon && !rainfall && !region) || loading) return;

    setInput("");
    setError(null);

    const structured_input: Record<string, any> = {};
    if (soilCarbon) structured_input.soil = { organic_carbon: parseFloat(soilCarbon) };
    if (rainfall) structured_input.climate = { rainfall };
    if (region) structured_input.location = { region };

    const userDisplayMsg = text || "Updated structured environmental state parameters.";
    setMessages((prev) => [...prev, { role: "user", content: userDisplayMsg }]);
    setLoading(true);

    try {
      const res: ChatResponse = await sendChatMessage({
        session_id: sessionId,
        conversation_id: conversationId || undefined,
        message: text || "Evaluating provided structured environmental metrics.",
        structured_input:
          Object.keys(structured_input).length > 0 ? structured_input : undefined,
      });

      setConversationId(res.conversation_id);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: res.response, response: res },
      ]);

      if (!res.needs_more_information) {
        window.sessionStorage.setItem(
          "darukaa_last_assessment",
          JSON.stringify(res.environmental_assessment)
        );
      }

      setSoilCarbon("");
      setRainfall("");
      setRegion("");
      setShowMetrics(false);
    } catch (e: any) {
      setError(e.message || "Something went wrong contacting the reasoning API.");
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="flex flex-col h-screen bg-slate-50/60 font-sans">
      <div className="px-8 py-4 border-b border-emerald-100/80 bg-white/80 backdrop-blur-md sticky top-0 z-20 flex items-center justify-between shadow-2xs">
        <div>
          <h1 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-600 animate-pulse" />
            AI Environmental Scientist
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Realtime persistent chat memory powered by evidence-grounded reasoning.
          </p>
        </div>

        <button
          onClick={() => setShowMetrics(!showMetrics)}
          className={`text-xs px-3.5 py-2 rounded-xl font-bold transition-all duration-200 flex items-center gap-2 cursor-pointer shadow-2xs ${
            showMetrics || activeMetricsCount > 0
              ? "bg-emerald-700 text-white shadow-emerald-900/10"
              : "bg-white text-emerald-900 border border-emerald-200 hover:bg-emerald-50"
          }`}
        >
          <span>{showMetrics ? "Hide Numeric Drawer" : "+ Add Specific Metrics"}</span>
          {activeMetricsCount > 0 && (
            <span className="w-4 h-4 rounded-full bg-emerald-200 text-emerald-950 text-[10px] font-black flex items-center justify-center">
              {activeMetricsCount}
            </span>
          )}
        </button>
      </div>

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-6 md:px-12 py-8 flex flex-col gap-5 max-w-4xl w-full mx-auto"
      >
        {messages.map((m, i) => (
          <div
            key={i}
            className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-2xl rounded-2xl px-5 py-4 text-sm leading-relaxed shadow-xs ${
                m.role === "user"
                  ? "bg-emerald-700 text-white font-medium rounded-br-xs"
                  : "bg-white text-slate-900 border border-emerald-100/80 rounded-bl-xs"
              }`}
            >
              <div className="whitespace-pre-wrap font-sans text-sm">{m.content}</div>

              {m.response && !m.response.needs_more_information && (
                <div className="mt-4 pt-3 border-t border-slate-100 flex flex-col gap-4">
                  {m.response.drivers.length > 0 && (
                    <div className="bg-slate-50 p-3 rounded-xl border border-slate-200/60">
                      <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-amber-500" /> Key Stress Drivers
                      </h4>
                      <ul className="list-disc list-inside text-xs text-slate-700 space-y-0.5">
                        {m.response.drivers.map((d, idx) => (
                          <li key={idx}>{d}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {m.response.relationships.length > 0 && (
                    <div>
                      <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" /> Causal Relationship Graph
                      </h4>
                      <div className="flex flex-col gap-1.5">
                        {m.response.relationships.slice(0, 6).map((r, idx) => (
                          <div
                            key={idx}
                            className="text-xs text-slate-800 font-mono bg-emerald-50/60 p-2 rounded-lg border border-emerald-100 flex items-center justify-between"
                          >
                            <span>
                              <strong>{r.source_metric}</strong> → <span className="font-bold text-emerald-800">{r.relationship}</span> → <strong>{r.target_metric}</strong>
                            </span>
                            <span className="text-[10px] font-bold uppercase bg-white text-slate-600 px-1.5 py-0.5 rounded border border-emerald-100">
                              {r.strength}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {m.response.recommendations.length > 0 && (
                    <div className="flex flex-col gap-2">
                      <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-sky-500" /> Actionable Interventions
                      </h4>
                      {m.response.recommendations.map((r, idx) => (
                        <RecommendationCard key={idx} rec={r} />
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border border-emerald-200/80 rounded-2xl px-4 py-3 text-xs text-slate-600 animate-pulse flex items-center gap-2 shadow-2xs">
              <span className="w-2 h-2 rounded-full bg-emerald-600 animate-ping" />
              Traversing multi-metric graph & verifying scientific evidence…
            </div>
          </div>
        )}

        {error && (
          <div className="text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-xl px-4 py-3">
            {error}
          </div>
        )}
      </div>

      {showMetrics && (
        <div className="max-w-4xl mx-auto w-full px-8 pb-2">
          <div className="bg-white border border-emerald-200/80 rounded-2xl p-4 shadow-lg">
            <h3 className="text-xs font-bold text-emerald-900 uppercase tracking-wider mb-2.5">
              Structured Metric Inputs
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
              <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200/80">
                <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                  Soil Carbon (%)
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={soilCarbon}
                  onChange={(e) => setSoilCarbon(e.target.value)}
                  placeholder="e.g. 0.8"
                  className="w-full text-xs bg-transparent text-slate-900 font-semibold focus:outline-none"
                />
              </div>
              <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200/80">
                <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                  Rainfall Level
                </label>
                <select
                  value={rainfall}
                  onChange={(e) => setRainfall(e.target.value)}
                  className="w-full text-xs bg-transparent text-slate-900 font-semibold focus:outline-none cursor-pointer"
                >
                  <option value="">Select rainfall</option>
                  <option value="low">Low / Arid</option>
                  <option value="moderate">Moderate</option>
                  <option value="high">High / Heavy</option>
                </select>
              </div>
              <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200/80">
                <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                  Region / Zone
                </label>
                <input
                  type="text"
                  value={region}
                  onChange={(e) => setRegion(e.target.value)}
                  placeholder="e.g. semi-arid"
                  className="w-full text-xs bg-transparent text-slate-900 font-semibold focus:outline-none"
                />
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="border-t border-emerald-100/80 bg-white/80 backdrop-blur-md px-8 py-4">
        <div className="max-w-4xl mx-auto flex gap-3 items-center">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={2}
            placeholder="Describe your land state, crop problems, or answer the assistant's questions…"
            className="flex-1 resize-none rounded-xl border border-emerald-200/80 bg-slate-50/50 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-600 focus:bg-white text-slate-900 placeholder:text-slate-400"
          />
          <button
            onClick={handleSend}
            disabled={loading || (!input.trim() && !soilCarbon && !rainfall && !region)}
            className="px-6 py-3 rounded-xl bg-emerald-700 hover:bg-emerald-800 text-white text-sm font-bold transition-all shadow-2xs disabled:opacity-40 shrink-0 cursor-pointer"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}