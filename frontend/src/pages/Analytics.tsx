/**
 * Workflow 4 — Analytics
 *
 * Separate page. Includes:
 * - Daily observations
 * - Signals over time
 * - Category distribution
 * - Heatmap
 * - Verification outcomes
 *
 * UI Principle: Every number has context.
 */

import { useEffect, useState } from "react";
import { getAnalytics, getHeatmap, getTimeline } from "../api";
import type { AnalyticsSummary, HeatmapPoint, TimelineEntry } from "../types";

const STATE_COLORS: Record<string, string> = {
  watch: "bg-blue-500",
  probable_hotspot: "bg-amber-500",
  high_confidence: "bg-red-500",
  archived: "bg-gray-500",
};

const CATEGORY_ICONS: Record<string, string> = {
  smoke: "💨", fire: "🔥", dust: "🌫️", chemical: "⚗️",
  water: "💧", noise: "🔊", gas_leak: "⚠️", construction_dust: "🏗️",
  sewage: "🚰", other: "❓",
};

export default function Analytics() {
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
  const [heatmap, setHeatmap] = useState<HeatmapPoint[]>([]);
  const [timeline, setTimeline] = useState<TimelineEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getAnalytics(), getHeatmap(), getTimeline()]).then(([a, h, t]) => {
      setAnalytics(a);
      setHeatmap(h);
      setTimeline(t);
      setLoading(false);
    });
  }, []);

  if (loading) return <div className="p-8 text-gray-400">Loading analytics...</div>;
  if (!analytics) return <div className="p-8 text-gray-400">Failed to load analytics</div>;

  // Group timeline by category for distribution
  const stateDistribution = Object.entries(analytics.signals_by_state);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Analytics</h1>

      {/* Summary cards */}
      <div className="grid grid-cols-4 gap-4">
        <Card title="Total Observations" value={analytics.total_observations} context="Citizen reports received" />
        <Card title="Total Signals" value={analytics.total_signals} context="Correlated environmental events" />
        <Card title="Active Signals" value={analytics.active_signals} context="Requiring attention" />
        <Card title="Avg Confidence" value={`${(analytics.avg_confidence * 100).toFixed(0)}%`} context="Across all signals" />
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Signals by State — bar chart */}
        <section className="bg-gray-800 rounded-lg p-5">
          <h2 className="text-sm font-semibold text-gray-300 mb-4">Signals by State</h2>
          <div className="space-y-3">
            {stateDistribution.map(([state, count]) => {
              const max = Math.max(...stateDistribution.map(([, c]) => c), 1);
              return (
                <div key={state} className="flex items-center gap-3">
                  <span className="w-24 text-xs text-gray-400 capitalize">{state.replace(/_/g, " ")}</span>
                  <div className="flex-1 bg-gray-700 rounded-full h-4">
                    <div
                      className={`h-4 rounded-full ${STATE_COLORS[state] ?? "bg-gray-500"}`}
                      style={{ width: `${(count / max) * 100}%` }}
                    />
                  </div>
                  <span className="w-8 text-right text-sm font-medium">{count}</span>
                </div>
              );
            })}
          </div>
        </section>

        {/* Heatmap */}
        <section className="bg-gray-800 rounded-lg p-5">
          <h2 className="text-sm font-semibold text-gray-300 mb-4">Signal Heatmap</h2>
          <div className="bg-gray-700/50 rounded h-48 relative overflow-hidden">
            {heatmap.length === 0 ? (
              <div className="flex items-center justify-center h-full text-gray-500 text-sm">
                No heatmap data
              </div>
            ) : (
              heatmap.map((point, i) => {
                const x = 10 + (i * 47) % 80;
                const y = 10 + (i * 31) % 80;
                const size = 8 + point.intensity * 20;
                return (
                  <div
                    key={i}
                    className="absolute rounded-full opacity-60"
                    style={{
                      left: `${x}%`,
                      top: `${y}%`,
                      width: size,
                      height: size,
                      backgroundColor:
                        point.dominant_state === "high_confidence" ? "#ef4444" :
                        point.dominant_state === "probable_hotspot" ? "#f59e0b" : "#3b82f6",
                    }}
                    title={`${point.signal_count} signals — ${point.dominant_state}`}
                  />
                );
              })
            )}
          </div>
          <p className="text-xs text-gray-500 mt-2">{heatmap.length} signal clusters</p>
        </section>
      </div>

      {/* Recent Timeline */}
      <section className="bg-gray-800 rounded-lg p-5">
        <h2 className="text-sm font-semibold text-gray-300 mb-4">Recent Activity</h2>
        <div className="space-y-2">
          {timeline.slice(0, 10).map((entry) => (
            <div key={entry.signal_id} className="flex items-center gap-3 text-sm">
              <span className={`w-2 h-2 rounded-full ${STATE_COLORS[entry.state]}`} />
              <span className="text-gray-400 w-16 text-xs">
                {new Date(entry.timestamp).toLocaleTimeString()}
              </span>
              <span className="capitalize">{entry.state.replace(/_/g, " ")}</span>
              <span className="text-gray-400">
                {(entry.composite_score * 100).toFixed(0)}% confidence
              </span>
              <span className="text-gray-500 text-xs ml-auto">
                {entry.observation_count} observations
              </span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function Card({ title, value, context }: { title: string; value: string | number; context: string }) {
  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <p className="text-xs text-gray-400">{title}</p>
      <p className="text-2xl font-bold text-white mt-1">{value}</p>
      <p className="text-xs text-gray-500 mt-1">{context}</p>
    </div>
  );
}
