import type {
  Signal,
  SignalState,
  ObservationCategory,
  Observation,
  AnalyticsSummary,
  Contribution,
} from "../types";

describe("TypeScript types compile correctly", () => {
  it("Signal type has required fields", () => {
    const signal: Signal = {
      id: "test",
      state: "watch" as SignalState,
      latitude: 19.0,
      longitude: 72.0,
      category: "smoke" as ObservationCategory,
      confidence_value: 0.5,
      contributing_observation_ids: [],
      contributions: [],
      environmental_context: {},
      version: 1,
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-01T00:00:00Z",
      archived_at: null,
    };
    expect(signal.id).toBe("test");
    expect(signal.state).toBe("watch");
  });

  it("Observation type has required fields", () => {
    const obs: Observation = {
      id: "test",
      fingerprint: null,
      content: "smoke visible",
      category: "smoke" as ObservationCategory,
      language: "en",
      latitude: 19.0,
      longitude: 72.0,
      status: "submitted",
      created_at: "2024-01-01T00:00:00Z",
      interpreted_at: null,
    };
    expect(obs.content).toBe("smoke visible");
  });

  it("AnalyticsSummary type has required fields", () => {
    const analytics: AnalyticsSummary = {
      total_observations: 100,
      total_signals: 10,
      active_signals: 5,
      high_confidence_signals: 2,
      avg_confidence: 0.65,
      signals_by_state: { watch: 3, probable_hotspot: 2, high_confidence: 2, archived: 3 },
    };
    expect(analytics.total_observations).toBe(100);
  });

  it("Contribution type has dimension_scores", () => {
    const contrib: Contribution = {
      observation_id: "obs-1",
      fingerprint: "abc",
      dimension_scores: { semantic: 0.8, spatial: 0.9, temporal: 0.7, independence: 1.0, environmental: 0.4 },
      contribution_score: 0.79,
      weighted_contribution: 0.55,
      evaluation_timestamp: "2024-01-01T00:00:00Z",
    };
    expect(contrib.dimension_scores.semantic).toBe(0.8);
  });
});
