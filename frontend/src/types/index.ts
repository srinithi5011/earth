export interface SoilState {
  ph: number | null;
  organic_carbon: number | null;
  moisture: number | null;
  nutrients: string | null;
}

export interface BiodiversityState {
  species_richness: string | null;
  habitat_diversity: string | null;
  pollinator_diversity: string | null;
  vegetation_diversity: string | null;
}

export interface ClimateState {
  temperature: string | null;
  rainfall: string | null;
  seasonality: string | null;
}

export interface HumanImpactState {
  pollution: string | null;
  deforestation: string | null;
  fragmentation: string | null;
  agricultural_pressure: string | null;
  urbanization: string | null;
}

export interface LocationState {
  latitude: number | null;
  longitude: number | null;
  region: string | null;
}

export interface EnvironmentalState {
  soil: SoilState;
  land_use: string | null;
  crop: string | null;
  biodiversity: BiodiversityState;
  climate: ClimateState;
  human_impact: HumanImpactState;
  location: LocationState;
}

export interface EvidenceItem {
  chunk_id: string;
  title: string | null;
  organization: string | null;
  source_url: string | null;
  publication_year: number | null;
  document_type: string | null;
  relevance: number;
  text_snippet: string | null;
}

export interface TimeHorizon {
  short_term?: string;
  medium_term?: string;
  long_term?: string;
}

export interface Recommendation {
  recommendation: string;
  scientific_reasoning: string;
  affected_metrics: string[];
  time_horizon: TimeHorizon;
  expected_effect: Record<string, string>;
  confidence: number;
  confidence_label: string;
  evidence: EvidenceItem[];
  intervention_category?: string;
}

export interface RelationshipEdge {
  source_metric: string;
  relationship: string;
  target_metric: string;
  direction: string;
  strength: string;
}

export interface ChatResponse {
  conversation_id: string;
  response: string;
  needs_more_information: boolean;
  missing_fields: string[];
  environmental_assessment: Record<string, any>;
  drivers: string[];
  relationships: RelationshipEdge[];
  recommendations: Recommendation[];
  evidence: EvidenceItem[];
  confidence: number;
  demo_mode: boolean;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  response?: ChatResponse;
}
