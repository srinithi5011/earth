import { useEffect, useState } from "react";
import { useConversationId } from "../hooks/useSession";
import { getConversation } from "../services/api";
import type { EnvironmentalState } from "../types";

type IconProps = { size?: number; className?: string };

const Icon = ({ size = 16, className = "" }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <circle cx="12" cy="12" r="8" />
  </svg>
);

function Field({ label, value }: { label: string; value: any }) {
  const isEmpty = value === null || value === undefined || value === "";
  return (
    <div className="flex justify-between items-center text-xs py-2 border-b border-slate-100 last:border-0">
      <span className="text-slate-500 font-medium">{label}</span>
      <span
        className={`font-semibold px-2.5 py-0.5 rounded-md font-mono ${
          isEmpty
            ? "text-slate-400 bg-slate-50"
            : "text-emerald-900 bg-emerald-50 border border-emerald-200/60"
        }`}
      >
        {isEmpty ? "—" : String(value)}
      </span>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white border border-emerald-100/80 rounded-2xl p-5 shadow-xs hover:border-emerald-200 transition-all">
      <h3 className="text-xs font-bold text-emerald-900 uppercase tracking-wider mb-3 flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-emerald-600" />
        {title}
      </h3>
      <div className="space-y-0.5">{children}</div>
    </div>
  );
}

export default function Profile() {
  const [conversationId] = useConversationId();
  const [state, setState] = useState<EnvironmentalState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!conversationId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    getConversation(conversationId)
      .then((c) => setState(c.environmental_context))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [conversationId]);

  return (
    <div className="min-h-screen bg-slate-50/60 p-8 font-sans">
      <div className="max-w-5xl mx-auto flex flex-col gap-6">
        <div>
          <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-600" />
            Environmental Profile
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Accumulated structured environmental state parameters[cite: 22].
          </p>
        </div>

        {error && (
          <div className="text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-xl px-4 py-3">
            {error}
          </div>
        )}

        {!loading && state && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Section title="Soil Health">
              <Field label="pH Level" value={state.soil?.ph} />
              <Field label="Organic Carbon (%)" value={state.soil?.organic_carbon} />
              <Field label="Moisture (%)" value={state.soil?.moisture} />
              <Field label="Nutrient Balance" value={state.soil?.nutrients} />
            </Section>

            <Section title="Climate Variables">
              <Field label="Temperature" value={state.climate?.temperature} />
              <Field label="Precipitation / Rainfall" value={state.climate?.rainfall} />
              <Field label="Seasonality Pattern" value={state.climate?.seasonality} />
            </Section>

            <Section title="Land Use & Crops">
              <Field label="Land Use Type" value={state.land_use} />
              <Field label="Primary Crop" value={state.crop} />
            </Section>

            <Section title="Biodiversity Indicators">
              <Field label="Species Richness" value={state.biodiversity?.species_richness} />
              <Field label="Habitat Diversity" value={state.biodiversity?.habitat_diversity} />
              <Field label="Pollinator Diversity" value={state.biodiversity?.pollinator_diversity} />
              <Field label="Vegetation Diversity" value={state.biodiversity?.vegetation_diversity} />
            </Section>

            <Section title="Human Impact Stressors">
              <Field label="Pollution Index" value={state.human_impact?.pollution} />
              <Field label="Deforestation Level" value={state.human_impact?.deforestation} />
              <Field label="Landscape Fragmentation" value={state.human_impact?.fragmentation} />
              <Field label="Agricultural Pressure" value={state.human_impact?.agricultural_pressure} />
              <Field label="Urban Expansion" value={state.human_impact?.urbanization} />
            </Section>

            <Section title="Geographic Location">
              <Field label="Regional Zone" value={state.location?.region} />
              <Field label="Latitude" value={state.location?.latitude} />
              <Field label="Longitude" value={state.location?.longitude} />
            </Section>
          </div>
        )}
      </div>
    </div>
  );
}