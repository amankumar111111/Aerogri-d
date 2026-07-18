/**
 * Workflow 2 — Municipal Command Centre
 *
 * Three questions:
 * 1. What is happening now?
 * 2. Where is it happening?
 * 3. What deserves attention first?
 *
 * Layout: Map (60%) | Signal Feed (40%)
 * Bottom: Selected Signal | Timeline | Evidence | Actions
 */

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { listSignals, getAnalytics, verifySignal, archiveSignal } from "../api";
import type { Signal, SignalState } from "../types";
import { useStore } from "../store";

const STATE_COLORS: Record<SignalState, string> = {
  watch: "bg-blue-500",
  probable_hotspot: "bg-amber-500",
  high_confidence: "bg-red-500",
  archived: "bg-gray-500",
};

const STATE_LABELS: Record<SignalState, string> = {
  watch: "Watch",
  probable_hotspot: "Probable Hotspot",
  high_confidence: "High Confidence",
  archived: "Archived",
};

export default function Dashboard() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { selectedSignalId, setSelectedSignal } = useStore();
  const navigate = useNavigate();

  useEffect(() => {
    const load = async () => {
      try {
        const [s, a] = await Promise.all([listSignals({ limit: 50 }), getAnalytics()]);
        setSignals(s);
        setAnalytics(a);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load data");
      } finally {
        setLoading(false);
      }
    };
    load();
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, []);

  const selected = signals.find((s) => s.id === selectedSignalId) ?? null;

  const handleAction = async (action: "verify" | "archive", id: string) => {
    try {
      if (action === "verify") await verifySignal(id);
      else await archiveSignal(id);
      setSignals((prev) => prev.filter((s) => s.id !== id));
      setSelectedSignal(null);
    } catch {
      // Handle error
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-96 text-gray-400">Loading signals...</div>;
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-96 text-center">
        <p className="text-red-400 text-lg mb-2">Failed to load dashboard</p>
        <p className="text-gray-500 text-sm mb-4">{error}</p>
        <button onClick={() => { setLoading(true); setError(null); }} className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      {/* Top bar — question 1: What is happening now? */}
      <div className="flex gap-4 mb-4">
        <div className="bg-gray-800 rounded-lg px-4 py-3 flex-1">
          <p className="text-xs text-gray-400">Active Signals</p>
          <p className="text-2xl font-bold text-white">{analytics?.active_signals ?? 0}</p>
        </div>
        <div className="bg-gray-800 rounded-lg px-4 py-3 flex-1">
          <p className="text-xs text-gray-400">High Confidence</p>
          <p className="text-2xl font-bold text-red-400">{analytics?.high_confidence_signals ?? 0}</p>
        </div>
        <div className="bg-gray-800 rounded-lg px-4 py-3 flex-1">
          <p className="text-xs text-gray-400">Today's Observations</p>
          <p className="text-2xl font-bold text-white">{analytics?.total_observations ?? 0}</p>
        </div>
        <div className="bg-gray-800 rounded-lg px-4 py-3 flex-1">
          <p className="text-xs text-gray-400">Avg Confidence</p>
          <p className="text-2xl font-bold text-emerald-400">
            {((analytics?.avg_confidence ?? 0) * 100).toFixed(0)}%
          </p>
        </div>
      </div>

      {/* Main content: Map (60%) + Signal Feed (40%) */}
      <div className="flex gap-4 flex-1 min-h-0">
        {/* Map — question 2: Where is it happening? */}
        <div className="w-[60%] bg-gray-800 rounded-lg relative overflow-hidden">
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <p className="text-4xl mb-2">🗺️</p>
              <p className="text-gray-400 text-sm">Signal Map</p>
              <p className="text-xs text-gray-500 mt-1">
                {signals.filter((s) => s.state !== "archived").length} active signals
              </p>
              {/* Signal dots on map */}
              <div className="absolute inset-0 pointer-events-none">
                {signals.filter((s) => s.state !== "archived").map((signal, i) => {
                  const x = 20 + (i * 60) % 60;
                  const y = 15 + (i * 37) % 70;
                  return (
                    <div
                      key={signal.id}
                      className={`absolute w-3 h-3 rounded-full ${STATE_COLORS[signal.state]} cursor-pointer pointer-events-auto opacity-80 hover:opacity-100 hover:scale-150 transition-all`}
                      style={{ left: `${x}%`, top: `${y}%` }}
                      onClick={() => setSelectedSignal(signal.id)}
                      title={`${STATE_LABELS[signal.state]} — ${signal.category}`}
                    />
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        {/* Signal Feed — question 3: What deserves attention first? */}
        <div className="w-[40%] bg-gray-800 rounded-lg flex flex-col">
          <div className="px-4 py-3 border-b border-gray-700">
            <h3 className="text-sm font-semibold">Signal Feed</h3>
            <p className="text-xs text-gray-400">Sorted by priority</p>
          </div>
          <div className="flex-1 overflow-y-auto">
            {signals
              .filter((s) => s.state !== "archived")
              .sort((a, b) => b.confidence_value - a.confidence_value)
              .map((signal) => (
                <div
                  key={signal.id}
                  onClick={() => setSelectedSignal(signal.id)}
                  className={`px-4 py-3 border-b border-gray-700/50 cursor-pointer transition-colors ${
                    selectedSignalId === signal.id
                      ? "bg-gray-700"
                      : "hover:bg-gray-700"
                  }`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`w-2 h-2 rounded-full ${STATE_COLORS[signal.state]}`} />
                    <span className="text-xs font-medium text-gray-300">
                      {STATE_LABELS[signal.state]}
                    </span>
                    <span className="text-xs text-gray-500 ml-auto">
                      {signal.contributing_observation_ids.length} obs
                    </span>
                  </div>
                  <p className="text-sm font-medium capitalize">{signal.category.replace("_", " ")}</p>
                  <p className="text-xs text-gray-400 mt-0.5">
                    Confidence: {(signal.confidence_value * 100).toFixed(0)}% · v{signal.version}
                  </p>
                </div>
              ))}
            {signals.filter((s) => s.state !== "archived").length === 0 && (
              <div className="p-8 text-center text-gray-500 text-sm">No active signals</div>
            )}
          </div>
        </div>
      </div>

      {/* Selected Signal panel — bottom */}
      {selected && (
        <div className="mt-4 bg-gray-800 rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-3">
              <span className={`w-3 h-3 rounded-full ${STATE_COLORS[selected.state]}`} />
              <h3 className="font-semibold capitalize">
                {selected.category.replace("_", " ")} — {STATE_LABELS[selected.state]}
              </h3>
              <span className="text-xs text-gray-400">
                Confidence: {(selected.confidence_value * 100).toFixed(0)}%
              </span>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => navigate(`/signals/${selected.id}`)}
                className="px-3 py-1 text-xs bg-gray-700 hover:bg-gray-600 rounded"
              >
                View Detail
              </button>
              {selected.state !== "archived" && (
                <>
                  <button
                    onClick={() => handleAction("verify", selected.id)}
                    className="px-3 py-1 text-xs bg-emerald-600 hover:bg-emerald-700 rounded"
                  >
                    Verify
                  </button>
                  <button
                    onClick={() => handleAction("archive", selected.id)}
                    className="px-3 py-1 text-xs bg-gray-600 hover:bg-gray-500 rounded"
                  >
                    Archive
                  </button>
                </>
              )}
            </div>
          </div>

          {/* Evidence convergence — show context, not raw numbers */}
          {selected.contributions.length > 0 && (
            <div className="grid grid-cols-4 gap-3 text-center">
              {["semantic", "spatial", "temporal", "environmental"].map((dim) => {
                const scores = selected.contributions.map((c) => c.dimension_scores[dim] ?? 0);
                const avg = scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : 0;
                return (
                  <div key={dim} className="bg-gray-700/50 rounded p-2">
                    <p className="text-xs text-gray-400 capitalize">{dim}</p>
                    <p className="text-lg font-bold text-white">{(avg * 100).toFixed(0)}%</p>
                  </div>
                );
              })}
            </div>
          )}

          <div className="mt-3 flex items-center gap-4 text-xs text-gray-400">
            <span>📍 {selected.latitude.toFixed(4)}, {selected.longitude.toFixed(4)}</span>
            <span>👁️ {selected.contributing_observation_ids.length} supporting observations</span>
            <span>🕐 {new Date(selected.updated_at).toLocaleTimeString()}</span>
          </div>
        </div>
      )}
    </div>
  );
}

interface AnalyticsSummary {
  total_observations: number;
  total_signals: number;
  active_signals: number;
  high_confidence_signals: number;
  avg_confidence: number;
}
