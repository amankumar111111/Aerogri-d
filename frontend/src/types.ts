/** TypeScript types matching the AEROGRID OpenAPI spec exactly. */

export type SignalState = "watch" | "probable_hotspot" | "high_confidence" | "archived";

export type ObservationCategory =
  | "smoke" | "dust" | "chemical" | "water" | "noise"
  | "fire" | "gas_leak" | "construction_dust" | "sewage" | "other";

export type ObservationStatus = "submitted" | "interpreted" | "correlated" | "archived";

export type Language = "en" | "hi" | "mr";

export interface ErrorResponse {
  error: {
    code: string;
    message: string;
    details: Array<{ field?: string; issue: string; received?: unknown }>;
    correlation_id: string;
    timestamp: string;
  };
}

export interface Observation {
  id: string;
  fingerprint: string | null;
  content: string;
  category: ObservationCategory;
  language: Language;
  latitude: number;
  longitude: number;
  status: ObservationStatus;
  created_at: string;
  interpreted_at: string | null;
}

export interface ObservationSubmitRequest {
  content: string;
  latitude: number;
  longitude: number;
  category: ObservationCategory;
  language?: Language;
  device_id: string;
}

export interface ObservationSubmitResponse {
  observation_id: string;
  fingerprint: string;
  status: ObservationStatus;
  tracking_ref: string;
}

export interface Contribution {
  observation_id: string;
  fingerprint: string;
  dimension_scores: Record<string, number>;
  contribution_score: number;
  weighted_contribution: number;
  evaluation_timestamp: string;
}

export interface Signal {
  id: string;
  state: SignalState;
  latitude: number;
  longitude: number;
  category: ObservationCategory;
  confidence_value: number;
  contributing_observation_ids: string[];
  contributions: Contribution[];
  environmental_context: Record<string, unknown>;
  version: number;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
}

export interface SignalActionResponse {
  signal_id: string;
  state: SignalState;
  message: string;
}

export interface AnalyticsSummary {
  total_observations: number;
  total_signals: number;
  active_signals: number;
  high_confidence_signals: number;
  avg_confidence: number;
  signals_by_state: Record<string, number>;
}

export interface HeatmapPoint {
  latitude: number;
  longitude: number;
  intensity: number;
  signal_count: number;
  dominant_state: SignalState;
}

export interface TimelineEntry {
  signal_id: string;
  state: SignalState;
  composite_score: number;
  observation_count: number;
  timestamp: string;
}

export interface HealthResponse {
  status: string;
  version: string;
}
