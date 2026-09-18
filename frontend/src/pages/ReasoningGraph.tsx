import React, { useEffect, useRef, useState } from "react";
import { getRelationships } from "../services/api";

export interface RelationshipEdge {
  id: string;
  source_metric: string;
  relationship: string;
  target_metric: string;
  direction: "positive" | "negative";
  strength: "weak" | "moderate" | "strong";
}

const GRAPH_TIERS: string[][] = [
  [
    "soil carbon",
    "rainfall",
    "temperature",
    "monoculture",
    "pesticide pressure",
    "deforestation",
    "urbanization",
    "soil moisture",
    "vegetation diversity",
    "agricultural pressure",
  ],
  [
    "microbial diversity",
    "water retention",
    "evapotranspiration",
    "habitat diversity",
    "pollinator abundance",
    "land fragmentation",
  ],
  ["water availability", "plant resilience", "habitat connectivity"],
  ["vegetation cover", "species survival", "species richness"],
  ["plant diversity", "pollinator diversity"],
];

export default function ReasoningGraph() {
  const [edges, setEdges] = useState<RelationshipEdge[]>([]);
  const [loading, setLoading] = useState(true);
  const containerRef = useRef<HTMLDivElement>(null);
  const nodeRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const [lineCoords, setLineCoords] = useState<
    { x1: number; y1: number; x2: number; y2: number; direction: string; id: string }[]
  >([]);

  useEffect(() => {
    getRelationships()
      .then((data) => setEdges(data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const calculateLines = () => {
    if (!containerRef.current) return;
    const containerRect = containerRef.current.getBoundingClientRect();
    const newCoords: typeof lineCoords = [];

    edges.forEach((edge) => {
      const srcEl = nodeRefs.current[edge.source_metric];
      const tgtEl = nodeRefs.current[edge.target_metric];

      if (srcEl && tgtEl) {
        const srcRect = srcEl.getBoundingClientRect();
        const tgtRect = tgtEl.getBoundingClientRect();

        newCoords.push({
          id: edge.id,
          direction: edge.direction,
          x1: srcRect.left + srcRect.width / 2 - containerRect.left,
          y1: srcRect.bottom - containerRect.top,
          x2: tgtRect.left + tgtRect.width / 2 - containerRect.left,
          y2: tgtRect.top - containerRect.top,
        });
      }
    });

    setLineCoords(newCoords);
  };

  useEffect(() => {
    if (!loading && edges.length > 0) {
      calculateLines();
      window.addEventListener("resize", calculateLines);
      return () => window.removeEventListener("resize", calculateLines);
    }
  }, [loading, edges]);

  return (
    <div className="min-h-screen bg-slate-50/60 p-8 font-sans">
      <div className="max-w-6xl mx-auto flex flex-col gap-6">
        <div>
          <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-600 animate-pulse" />
            Deterministic Reasoning Graph
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Hierarchical causal node mapping traversed by the BFS engine. Every edge represents a verified relationship.
          </p>
        </div>

        {/* Clean Light Canvas Card */}
        <div className="bg-white border border-emerald-100/80 rounded-2xl p-6 shadow-xs">
          <div ref={containerRef} className="relative flex flex-col gap-12 py-6 min-h-[500px]">
            {/* Render Node Cards */}
            {GRAPH_TIERS.map((tierMetrics, tierIdx) => (
              <div key={tierIdx} className="flex justify-center items-center gap-3 flex-wrap z-10">
                {tierMetrics.map((metric) => (
                  <div
                    key={metric}
                    ref={(el) => (nodeRefs.current[metric] = el)}
                    className="px-3.5 py-2 rounded-xl border border-emerald-200/80 bg-emerald-50/60 text-emerald-950 text-xs font-mono font-bold shadow-2xs hover:border-emerald-400 hover:bg-emerald-50 transition-all cursor-pointer"
                  >
                    {metric}
                  </div>
                ))}
              </div>
            ))}

            {/* Dynamic SVG Connecting Lines */}
            <svg className="absolute inset-0 w-full h-full pointer-events-none z-0">
              <defs>
                <marker
                  id="arrow-pos"
                  viewBox="0 0 10 10"
                  refX="5"
                  refY="5"
                  markerWidth="5"
                  markerHeight="5"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#15803d" />
                </marker>
                <marker
                  id="arrow-neg"
                  viewBox="0 0 10 10"
                  refX="5"
                  refY="5"
                  markerWidth="5"
                  markerHeight="5"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#c2410c" />
                </marker>
              </defs>

              {lineCoords.map((line) => (
                <line
                  key={line.id}
                  x1={line.x1}
                  y1={line.y1}
                  x2={line.x2}
                  y2={line.y2}
                  stroke={line.direction === "positive" ? "#15803d" : "#c2410c"}
                  strokeWidth="1.5"
                  strokeOpacity="0.5"
                  markerEnd={line.direction === "positive" ? "url(#arrow-pos)" : "url(#arrow-neg)"}
                />
              ))}
            </svg>
          </div>

          {/* Graph Legend Footer */}
          <div className="border-t border-slate-100 pt-4 flex items-center justify-between text-xs text-slate-500 font-medium">
            <div>
              <span className="text-emerald-700 font-bold">Green = Positive Effect</span> |{" "}
              <span className="text-orange-700 font-bold">Orange/Red = Negative Effect</span>
            </div>
            <div className="font-mono text-[11px] bg-slate-50 text-slate-700 px-3 py-1 rounded-lg border border-slate-200/80">
              Total Stored Edges: {edges.length}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}