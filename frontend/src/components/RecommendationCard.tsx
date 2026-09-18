import type { Recommendation } from "../types";

const CONFIDENCE_STYLES: Record<string, string> = {
  High: "text-moss-700 bg-moss-100 border-moss-300",
  Medium: "text-soil-500 bg-soil-500/10 border-soil-500/30",
  Low: "text-alert bg-alert/10 border-alert/30",
};

export default function RecommendationCard({ rec }: { rec: Recommendation }) {
  const confStyle = CONFIDENCE_STYLES[rec.confidence_label] || CONFIDENCE_STYLES.Low;
  const isInsufficient = rec.recommendation.startsWith("Evidence insufficient");

  return (
    <div className="border border-moss-100 rounded-lg bg-white p-4 shadow-sm flex flex-col gap-3">
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-medium text-ink leading-snug">{rec.recommendation}</p>
        <span className={`shrink-0 text-xs font-semibold px-2 py-0.5 rounded-full border ${confStyle}`}>
          Evidence Confidence: {rec.confidence_label}
        </span>
      </div>

      {!isInsufficient && (
        <>
          <p className="text-xs text-ink/60 leading-relaxed">{rec.scientific_reasoning}</p>

          {rec.affected_metrics.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {rec.affected_metrics.map((m) => (
                <span
                  key={m}
                  className="text-[11px] px-2 py-0.5 rounded bg-moss-50 text-moss-700 border border-moss-100"
                >
                  {m.replace(/_/g, " ")}
                  {rec.expected_effect[m] ? ` (${rec.expected_effect[m]})` : ""}
                </span>
              ))}
            </div>
          )}

          {(rec.time_horizon.short_term || rec.time_horizon.medium_term || rec.time_horizon.long_term) && (
            <div className="grid grid-cols-3 gap-2 text-[11px] text-ink/60 border-t border-moss-100 pt-2">
              <div>
                <span className="font-semibold block text-ink/70">Short-term</span>
                {rec.time_horizon.short_term || "—"}
              </div>
              <div>
                <span className="font-semibold block text-ink/70">Medium-term</span>
                {rec.time_horizon.medium_term || "—"}
              </div>
              <div>
                <span className="font-semibold block text-ink/70">Long-term</span>
                {rec.time_horizon.long_term || "—"}
              </div>
            </div>
          )}

          {rec.evidence.length > 0 && (
            <div className="border-t border-moss-100 pt-2 flex flex-col gap-1">
              <span className="text-[11px] font-semibold text-ink/70">Evidence</span>
              {rec.evidence.map((e) => (
                <div key={e.chunk_id} className="text-[11px] text-ink/50">
                  <span className="font-medium text-ink/70">{e.title}</span>
                  {e.organization ? ` — ${e.organization}` : ""}
                  {e.publication_year ? ` (${e.publication_year})` : ""}
                  {" · relevance "}
                  {(e.relevance * 100).toFixed(0)}%
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
