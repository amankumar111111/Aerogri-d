/**
 * Workflow 3 — Signal Detail
 *
 * When a signal is clicked:
 * Show: Location, Classification, Evidence, Timeline, Environmental Context,
 *       Supporting Observations, Explainability
 *
 * Never show raw JSON.
 */

import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getSignal, getObservation } from "../api";
import type { Signal, Observation } from "../types";

const STATE_COLORS: Record<string, string> = {
  watch: "bg-blue-500 text-blue-100",
  probable_hotspot: "bg-amber-500 text-amber-100",
  high_confidence: "bg-red-500 text-red-100",
  archived: "bg-gray-500 text-gray-100",
};

const STATE_LABELS: Record<string, string> = {
  watch: "Watch",
  probable_hotspot: "Probable Hotspot",
  high_confidence: "High Confidence",
  archived: "Archived",
};

export default function SignalDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [signal, setSignal] = useState<Signal | null>(null);
  const [observations, setObservations] = useState<Map<string, Observation>>(new Map());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    getSignal(id).then(async (s) => {
      setSignal(s);
      // Fetch contributing observations
      const obsMap = new Map<string, Observation>();
      await Promise.all(
        s.contributing_observation_ids.slice(0, 10).map(async (obsId) => {
          try {
            const obs = await getObservation(obsId);
            obsMap.set(obsId, obs);
          } catch {
            // Observation may not exist yet
          }
        })
      );
      setObservations(obsMap);
      setLoading(false);
    });
  }, [id]);

  if (loading) return <div className="p-8 text-gray-400">Loading signal...</div>;
  if (!signal) return <div className="p-8 text-gray-400">Signal not found</div>;

  // Compute explainability from contributions
  const avgDimension = (dim: string) => {
    const scores = signal.contributions.map((c) => c.dimension_scores[dim] ?? 0);
    return scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : 0;
  };

  return (
    <div className="max-w-4xl mx-auto">
      <button onClick={() => navigate(-1)} className="text-sm text-gray-400 hover:text-white mb-4">
        ← Back
      </button>

      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${STATE_COLORS[signal.state]}`}>
          {STATE_LABELS[signal.state]}
        </span>
        <h1 className="text-2xl font-bold capitalize">{signal.category.replace("_", " ")}</h1>
        <span className="text-gray-400 text-sm">
          Confidence: {(signal.confidence_value * 100).toFixed(0)}%
        </span>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Left column: Evidence + Explainability */}
        <div className="col-span-2 space-y-6">
          {/* Evidence Convergence — context, not raw JSON */}
          <section className="bg-gray-800 rounded-lg p-5">
            <h2 className="text-sm font-semibold text-gray-300 mb-4">Evidence Convergence</h2>
            <div className="grid grid-cols-2 gap-4">
              {[
                { dim: "semantic", label: "Semantic Match", desc: "Do observations describe the same event?" },
                { dim: "spatial", label: "Spatial Proximity", desc: "Are observations geographically close?" },
                { dim: "temporal", label: "Temporal Proximity", desc: "Were observations reported around the same time?" },
                { dim: "environmental", label: "Environmental Context", desc: "Does weather/satellite data corroborate?" },
              ].map(({ dim, label, desc }) => {
                const score = avgDimension(dim);
                const pct = (score * 100).toFixed(0);
                const level = score >= 0.7 ? "High" : score >= 0.4 ? "Medium" : "Low";
                return (
                  <div key={dim} className="bg-gray-700/50 rounded p-3">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium">{label}</span>
                      <span className={`text-sm font-bold ${score >= 0.7 ? "text-emerald-400" : score >= 0.4 ? "text-amber-400" : "text-gray-400"}`}>
                        {pct}%
                      </span>
                    </div>
                    <div className="w-full bg-gray-600 rounded-full h-2 mb-1">
                      <div
                        className={`h-2 rounded-full ${score >= 0.7 ? "bg-emerald-500" : score >= 0.4 ? "bg-amber-500" : "bg-gray-500"}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <p className="text-xs text-gray-400">{desc}</p>
                    <p className="text-xs text-gray-500 mt-1">
                      {signal.contributions.length} contributing observations
                    </p>
                  </div>
                );
              })}
            </div>
          </section>

          {/* Supporting Observations */}
          <section className="bg-gray-800 rounded-lg p-5">
            <h2 className="text-sm font-semibold text-gray-300 mb-4">
              Supporting Observations ({signal.contributing_observation_ids.length})
            </h2>
            <div className="space-y-2">
              {signal.contributions.map((contrib) => {
                const obs = observations.get(contrib.observation_id);
                return (
                  <div key={contrib.observation_id} className="bg-gray-700/50 rounded p-3 flex items-center gap-3">
                    <div className="text-2xl">
                      {obs?.category === "smoke" ? "💨" : obs?.category === "fire" ? "🔥" : "👁️"}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm truncate">{obs?.content || "Observation"}</p>
                      <p className="text-xs text-gray-400">
                        {contrib.contribution_score > 0.7 ? "Strong" : contrib.contribution_score > 0.4 ? "Moderate" : "Weak"} evidence · {new Date(contrib.evaluation_timestamp).toLocaleTimeString()}
                      </p>
                    </div>
                    <span className="text-xs font-mono text-gray-500">
                      {(contrib.contribution_score * 100).toFixed(0)}%
                    </span>
                  </div>
                );
              })}
            </div>
          </section>
        </div>

        {/* Right column: Metadata + Environmental Context */}
        <div className="space-y-6">
          {/* Location */}
          <section className="bg-gray-800 rounded-lg p-5">
            <h2 className="text-sm font-semibold text-gray-300 mb-3">Location</h2>
            <div className="bg-gray-700/50 rounded h-32 flex items-center justify-center">
              <div className="text-center">
                <p className="text-2xl">📍</p>
                <p className="text-sm text-gray-300 mt-1">
                  {signal.latitude.toFixed(4)}, {signal.longitude.toFixed(4)}
                </p>
              </div>
            </div>
          </section>

          {/* Environmental Context — human-readable */}
          <section className="bg-gray-800 rounded-lg p-5">
            <h2 className="text-sm font-semibold text-gray-300 mb-3">Environmental Context</h2>
            <div className="space-y-2">
              {Object.entries(signal.environmental_context).map(([key, value]) => (
                <div key={key} className="flex justify-between text-sm">
                  <span className="text-gray-400 capitalize">{key.replace(/_/g, " ")}</span>
                  <span className="text-white">
                    {typeof value === "boolean" ? (value ? "Yes" : "No") : String(value)}
                  </span>
                </div>
              ))}
              {Object.keys(signal.environmental_context).length === 0 && (
                <p className="text-xs text-gray-500">No environmental data available</p>
              )}
            </div>
          </section>

          {/* Signal Metadata */}
          <section className="bg-gray-800 rounded-lg p-5">
            <h2 className="text-sm font-semibold text-gray-300 mb-3">Signal Info</h2>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Version</span>
                <span className="text-white">v{signal.version}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Created</span>
                <span className="text-white">{new Date(signal.created_at).toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Updated</span>
                <span className="text-white">{new Date(signal.updated_at).toLocaleString()}</span>
              </div>
              {signal.archived_at && (
                <div className="flex justify-between">
                  <span className="text-gray-400">Archived</span>
                  <span className="text-white">{new Date(signal.archived_at).toLocaleString()}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-gray-400">ID</span>
                <span className="text-white font-mono text-xs">{signal.id.slice(0, 8)}...</span>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
