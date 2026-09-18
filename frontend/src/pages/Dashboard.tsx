import { useEffect, useRef, useState } from "react";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import MetricCard from "../components/MetricCard";
import { getHealth, getConversation } from "../services/api";
import { useConversationId } from "../hooks/useSession";
import type { EnvironmentalState } from "../types";

// Fix missing marker icons in Leaflet + bundler environments
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
});

type IconProps = { size?: number; className?: string };

const Icon = ({ size = 24, className = "" }: IconProps) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
    <path d="M12 3C7 5 4 9 4 14c0 4 3 7 8 7s8-3 8-7c0-5-3-9-8-11Z" />
    <path d="M12 3v18M12 12c-3-1-5-3-6-5M12 15c3-1 5-3 6-5" />
  </svg>
);

const AlertCircle = (props: IconProps) => <Icon {...props} />;
const Leaf = (props: IconProps) => <Icon {...props} />;
const MapPinned = (props: IconProps) => <Icon {...props} />;
const Satellite = (props: IconProps) => <Icon {...props} />;
const Sprout = (props: IconProps) => <Icon {...props} />;

export interface ForestPreset {
  id: string;
  name: string;
  region: string;
  coordinates: [number, number];
  zoom: number;
  ecotype: string;
}

const FOREST_PRESETS: ForestPreset[] = [
  {
    id: "western_ghats",
    name: "Western Ghats Hotspot",
    region: "Maharashtra / Goa, India",
    coordinates: [15.5497, 74.2532],
    zoom: 11,
    ecotype: "Tropical Moist Broadleaf",
  },
  {
    id: "amazon",
    name: "Amazon Rainforest",
    region: "Manaus, Brazil",
    coordinates: [-3.4653, -62.2159],
    zoom: 11,
    ecotype: "Tropical Rainforest",
  },
  {
    id: "black_forest",
    name: "Black Forest (Schwarzwald)",
    region: "Baden-Württemberg, Germany",
    coordinates: [48.2721, 8.1633],
    zoom: 11,
    ecotype: "Temperate Coniferous Forest",
  },
  {
    id: "congo",
    name: "Congo Basin Swamp Forest",
    region: "Democratic Republic of the Congo",
    coordinates: [-0.7893, 22.9375],
    zoom: 10,
    ecotype: "Lowland Swamp Forest",
  },
  {
    id: "redwood",
    name: "Redwood National Park",
    region: "California, USA",
    coordinates: [41.2132, -124.0046],
    zoom: 12,
    ecotype: "Temperate Rainforest",
  },
  {
    id: "boreal",
    name: "Taiga Boreal Canopy",
    region: "Siberia, Russia",
    coordinates: [61.524, 105.3188],
    zoom: 9,
    ecotype: "Subarctic Boreal Taiga",
  },
];

const METRICS = [
  { title: "Soil Health", key: "soil_health", description: "Derived from organic carbon, pH, and moisture." },
  { title: "Water Availability", key: "water_availability", description: "Derived from rainfall and reported water access." },
  { title: "Biodiversity", key: "biodiversity", description: "Derived from species richness and habitat diversity." },
  { title: "Climate Stress", key: "climate_stress", description: "Derived from temperature and rainfall extremes." },
  { title: "Human Impact", key: "human_impact", description: "Derived from pollution, deforestation, fragmentation." },
];

const FOREST_IMAGE = "https://commons.wikimedia.org/wiki/Special:FilePath/Aerial_view_of_a_forest_(Unsplash).jpg";

// High-visibility Responsive Leaflet Map Wrapper
function LeafletMap({ center, zoom, region }: { center: [number, number]; zoom: number; region?: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markerRef = useRef<L.Marker | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const map = L.map(containerRef.current, { scrollWheelZoom: true, zoomControl: true }).setView(center, zoom);

    L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
      attribution: "Tiles &copy; Esri &mdash; Source: Esri, USDA, USGS",
      maxZoom: 18,
    }).addTo(map);

    if (region) {
      markerRef.current = L.marker(center).addTo(map).bindPopup(region);
    }
    mapRef.current = map;

    // Fix alignment and view calculation glitches
    const timer = setTimeout(() => {
      map.invalidateSize();
    }, 200);

    return () => {
      clearTimeout(timer);
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (mapRef.current) {
      mapRef.current.invalidateSize();
      mapRef.current.flyTo(center, zoom, { duration: 1.2 });
      if (markerRef.current) {
        markerRef.current.setLatLng(center);
        if (region) markerRef.current.bindPopup(region).openPopup();
      } else if (region) {
        markerRef.current = L.marker(center).addTo(mapRef.current).bindPopup(region);
        markerRef.current.openPopup();
      }
    }
  }, [center[0], center[1], zoom, region]);

  return <div ref={containerRef} className="w-full h-full min-h-[450px] z-0 rounded-lg overflow-hidden" />;
}

export default function Dashboard() {
  const [conversationId] = useConversationId();
  const [health, setHealth] = useState<{ status: string; demo_mode: boolean; vector_backend: string } | null>(null);
  const [envState, setEnvState] = useState<EnvironmentalState | null>(null);
  const [assessment, setAssessment] = useState<Record<string, string> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [selectedPreset, setSelectedPreset] = useState<ForestPreset | null>(FOREST_PRESETS[0]);

  useEffect(() => {
    try {
      const raw = window.sessionStorage.getItem("darukaa_last_assessment");
      if (raw) setAssessment(JSON.parse(raw));
    } catch {
      setAssessment(null);
    }
  }, []);

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));

    if (conversationId) {
      getConversation(conversationId)
        .then((c) => {
          if (c && c.environmental_context) {
            setEnvState(c.environmental_context);
            if (c.environmental_context?.location?.latitude) {
              setSelectedPreset(null);
            }
          }
        })
        .catch(() => {});
    }
  }, [conversationId]);

  const activeLat = selectedPreset
    ? selectedPreset.coordinates[0]
    : envState?.location?.latitude ?? 15.5497;

  const activeLng = selectedPreset
    ? selectedPreset.coordinates[1]
    : envState?.location?.longitude ?? 74.2532;

  const activeZoom = selectedPreset
    ? selectedPreset.zoom
    : envState?.location?.latitude ? 12 : 11;

  const activeRegionLabel = selectedPreset
    ? `${selectedPreset.name} (${selectedPreset.ecotype})`
    : envState?.location?.region || "Assessed Land Plot";

  return (
    <div className="flex flex-col gap-6 pb-10 bg-slate-50 font-sans min-h-screen w-full">
      {/* Hero Banner */}
      <div className="relative h-52 md:h-60 w-full overflow-hidden">
        <img
          src={FOREST_IMAGE}
          alt="Aerial view of forest canopy"
          className="absolute inset-0 w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-ink/90 via-ink/40 to-moss-700/30" />

        <div className="relative h-full flex flex-col justify-end px-8 pb-6 max-w-7xl mx-auto w-full">
          <div>
            <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-moss-100 bg-white/10 backdrop-blur-sm border border-white/20 rounded-full px-2.5 py-1 mb-2">
              <span className="w-1.5 h-1.5 rounded-full bg-moss-300 animate-pulse" />
              Live Biodiversity Intelligence Engine
            </span>
            <h1 className="text-2xl md:text-3xl font-bold text-white tracking-tight">
              Environmental Health Overview
            </h1>
          </div>
        </div>
      </div>

      {/* Main Container - Expanded Width */}
      <div className="px-6 md:px-10 max-w-7xl mx-auto w-full flex flex-col gap-6">
        {error && (
          <div className="flex items-center gap-2 text-xs text-alert bg-alert/10 border border-alert/30 rounded-md px-3 py-2">
            <AlertCircle size={14} />
            Backend unreachable: {error}.
          </div>
        )}

        {/* Status Header */}
        {health && (
          <div className="flex items-center gap-3 text-xs text-ink/60 bg-white p-3.5 rounded-xl border border-moss-100 shadow-2xs">
            <span className="relative flex h-2 w-2">
              {health.status === "ok" && (
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-moss-400 opacity-60" />
              )}
              <span className={`relative inline-flex rounded-full h-2 w-2 ${health.status === "ok" ? "bg-moss-500" : "bg-alert"}`} />
            </span>
            <span>Status: <strong className="text-ink">{health.status}</strong></span>
            <span>·</span>
            <span>Vector backend: <strong className="text-ink">{health.vector_backend}</strong></span>
          </div>
        )}

        {/* Metrics Grid */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {loading
            ? Array.from({ length: 5 }).map((_, i) => <div key={i} className="h-24 bg-moss-100/40 animate-pulse rounded-lg" />)
            : METRICS.map((m) => (
                <MetricCard
                  key={m.key}
                  title={m.title}
                  status={assessment?.[m.key] || "Unknown"}
                  description={m.description}
                />
              ))}
        </div>

        {/* Broader Full-Width Satellite Map Container */}
        <div className="relative overflow-hidden rounded-2xl border border-moss-200/80 shadow-md bg-white w-full">
          {/* Controls Bar */}
          <div className="p-4 bg-white border-b border-moss-100 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <MapPinned size={18} className="text-moss-600" />
              <span className="text-sm font-bold text-ink">Global Real Forest Canopy Observation</span>
            </div>

            <div className="flex items-center gap-2">
              <label htmlFor="forest-select" className="text-xs text-ink/70 font-semibold">Select Canopy Location:</label>
              <select
                id="forest-select"
                value={selectedPreset?.id || "custom"}
                onChange={(e) => {
                  const val = e.target.value;
                  if (val === "custom") {
                    setSelectedPreset(null);
                  } else {
                    const preset = FOREST_PRESETS.find((p) => p.id === val);
                    if (preset) setSelectedPreset(preset);
                  }
                }}
                className="text-xs border border-moss-300 rounded-lg px-3 py-2 bg-moss-50/80 text-ink font-semibold focus:outline-none focus:ring-2 focus:ring-moss-400 cursor-pointer shadow-2xs"
              >
                {FOREST_PRESETS.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.region})
                  </option>
                ))}
                {envState?.location?.latitude && (
                  <option value="custom">Current Session Target Plot</option>
                )}
              </select>
            </div>
          </div>

          {/* Broad Map View Canvas */}
          <div className="relative w-full h-[500px] bg-slate-900">
            <LeafletMap
              center={[activeLat, activeLng]}
              zoom={activeZoom}
              region={activeRegionLabel}
            />

            <div className="absolute top-4 left-4 z-[1000] inline-flex items-center gap-2 text-xs font-semibold text-white bg-black/75 backdrop-blur-md border border-white/20 rounded-full px-3.5 py-1.5 shadow-md">
              <Satellite size={14} className="text-emerald-400" />
              Interactive High-Resolution Satellite View
            </div>
          </div>

          {/* Detailed Footer Info */}
          <div className="p-4 bg-white border-t border-moss-100 flex items-center justify-between text-xs">
            <div>
              <h3 className="text-ink font-bold text-sm flex items-center gap-2">
                {activeRegionLabel}
              </h3>
              <p className="text-ink/60 text-xs mt-0.5">
                Displays real canopy density, agricultural boundaries, and topography.
              </p>
            </div>
            <div className="font-mono text-xs font-semibold text-moss-800 bg-moss-50 px-3 py-1.5 rounded-lg border border-moss-200">
              {activeLat.toFixed(4)}°, {activeLng.toFixed(4)}°
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}