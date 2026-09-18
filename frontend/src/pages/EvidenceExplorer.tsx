import { useEffect, useState } from "react";
import { getEvidence } from "../services/api";

type IconProps = { size?: number; className?: string };

const Icon = ({ size = 16, className = "" }: IconProps) => (
  <svg
    width={size}
    height={size}
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <circle cx="12" cy="12" r="8" />
  </svg>
);

const ChevronDown = ({ size = 16, className = "" }: IconProps) => (
  <svg
    width={size}
    height={size}
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="m6 9 6 6 6-6" />
  </svg>
);

const ExternalLink = ({ size = 14, className = "" }: IconProps) => (
  <svg
    width={size}
    height={size}
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M15 3h6v6" />
    <path d="M10 14 21 3" />
    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
  </svg>
);

const Library = ({ size = 18, className = "" }: IconProps) => (
  <svg
    width={size}
    height={size}
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="m16 6 4 2v12l-4-2V6Z" />
    <path d="m8 6 4-2 4 2v12l-4 2-4-2V6Z" />
    <path d="m4 8 4-2v12l-4 2V8Z" />
  </svg>
);

interface EvidenceRow {
  chunk_id: string;
  document_id: string;
  title: string;
  organization: string;
  publication_year: number | null;
  topic: string | null;
  region: string | null;
  document_type: string | null;
  source_url: string | null;
  credibility_tier: string;
  text: string;
}

const CREDIBILITY_STYLES: Record<string, string> = {
  authoritative: "bg-emerald-100/80 text-emerald-900 border-emerald-300",
  established: "bg-amber-100/80 text-amber-900 border-amber-300",
  emerging: "bg-rose-100/80 text-rose-900 border-rose-300",
};

export default function EvidenceExplorer() {
  const [rows, setRows] = useState<EvidenceRow[]>([]);
  const [topicFilter, setTopicFilter] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getEvidence(topicFilter ? { topic: topicFilter } : undefined)
      .then(setRows)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [topicFilter]);

  const topics = ["soil", "biodiversity", "climate", "human_impact", "land_use"];

  return (
    <div className="min-h-screen bg-slate-50/60 p-8 font-sans">
      <div className="max-w-6xl mx-auto flex flex-col gap-6">
        <div>
          <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
            <Library size={20} className="text-emerald-700" />
            Evidence Explorer
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Curated scientific knowledge corpus. Click any row to expand the full extracted text chunk[cite: 22].
          </p>
        </div>

        {/* Filter Pills */}
        <div className="flex gap-2 flex-wrap">
          {["", ...topics].map((t) => {
            const isActive = topicFilter === t;
            return (
              <button
                key={t || "all"}
                onClick={() => setTopicFilter(t)}
                className={`text-xs px-4 py-2 rounded-xl font-semibold capitalize transition-all cursor-pointer ${
                  isActive
                    ? "bg-emerald-700 text-white shadow-2xs"
                    : "bg-white text-slate-600 border border-emerald-100/80 hover:bg-slate-100"
                }`}
              >
                {t === "" ? "All Topics" : t.replace("_", " ")}
              </button>
            );
          })}
        </div>

        {error && (
          <div className="text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-xl px-4 py-3">
            {error}
          </div>
        )}

        {/* Interactive Evidence Table */}
        <div className="bg-white border border-emerald-100/80 rounded-2xl overflow-hidden shadow-xs">
          {loading ? (
            <div className="p-6 flex flex-col gap-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="h-12 bg-slate-100/80 animate-pulse rounded-xl" />
              ))}
            </div>
          ) : (
            <table className="w-full text-xs text-left">
              <thead className="bg-slate-50 text-slate-700 font-bold border-b border-emerald-100/80 uppercase tracking-wider">
                <tr>
                  <th className="px-5 py-3.5">Document Source</th>
                  <th className="px-5 py-3.5">Organization</th>
                  <th className="px-5 py-3.5">Year</th>
                  <th className="px-5 py-3.5">Topic</th>
                  <th className="px-5 py-3.5">Credibility</th>
                  <th className="px-5 py-3.5 w-8" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {rows.map((r) => {
                  const isOpen = expanded === r.chunk_id;
                  const credStyle =
                    CREDIBILITY_STYLES[r.credibility_tier] ||
                    "bg-slate-100 text-slate-700 border-slate-200";

                  return (
                    <tr key={r.chunk_id} className="contents">
                      {/* Parent Row */}
                      <tr
                        onClick={() => setExpanded(isOpen ? null : r.chunk_id)}
                        className={`hover:bg-emerald-50/50 cursor-pointer transition-colors ${
                          isOpen ? "bg-emerald-50/30" : ""
                        }`}
                      >
                        <td className="px-5 py-3.5 font-bold text-slate-900">{r.title}</td>
                        <td className="px-5 py-3.5 text-slate-500">{r.organization}</td>
                        <td className="px-5 py-3.5 text-slate-500 font-mono">
                          {r.publication_year || "—"}
                        </td>
                        <td className="px-5 py-3.5 text-slate-600 capitalize">
                          {(r.topic || "").replace("_", " ")}
                        </td>
                        <td className="px-5 py-3.5">
                          <span
                            className={`inline-block text-[10px] font-bold uppercase px-2.5 py-1 rounded-md border ${credStyle}`}
                          >
                            {r.credibility_tier}
                          </span>
                        </td>
                        <td className="px-5 py-3.5">
                          <ChevronDown
                            size={16}
                            className={`text-slate-400 transition-transform duration-200 ${
                              isOpen ? "rotate-180 text-emerald-700" : ""
                            }`}
                          />
                        </td>
                      </tr>

                      {/* Expandable Chunk Content Drawer Row */}
                      {isOpen && (
                        <tr className="bg-emerald-50/20">
                          <td colSpan={6} className="px-6 py-4 border-t border-emerald-100/60">
                            <div className="flex flex-col gap-2 text-slate-700 leading-relaxed bg-white p-4 rounded-xl border border-emerald-100/80 shadow-2xs">
                              <span className="text-[11px] font-bold uppercase text-emerald-800 tracking-wider">
                                Extracted Evidence Chunk Text
                              </span>
                              <p className="text-xs italic text-slate-800 font-serif">
                                "{r.text}"
                              </p>

                              {r.source_url && (
                                <div className="mt-2 pt-2 border-t border-slate-100 flex items-center justify-between">
                                  <span className="text-[10px] text-slate-400">
                                    Document ID: {r.document_id}
                                  </span>
                                  <a
                                    href={r.source_url}
                                    target="_blank"
                                    rel="noreferrer"
                                    onClick={(e) => e.stopPropagation()}
                                    className="text-emerald-700 hover:text-emerald-800 font-semibold inline-flex items-center gap-1 text-xs hover:underline"
                                  >
                                    View Primary Source Document
                                    <ExternalLink size={12} />
                                  </a>
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}

          {!loading && rows.length === 0 && (
            <div className="p-12 text-center text-sm text-slate-400">
              No evidence chunks found for this filter query.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}