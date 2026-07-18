/**
 * Workflow 5 — Admin (Hidden)
 *
 * Used for:
 * - Provider health
 * - Policy version
 * - Audit
 * - Calibration
 */

import { useEffect, useState } from "react";
import { getHealth } from "../api";

interface ProviderHealth {
  name: string;
  status: "healthy" | "degraded" | "down";
  lastCheck: string;
  latency: string;
}

const MOCK_PROVIDERS: ProviderHealth[] = [
  { name: "Gemini (Interpreter)", status: "healthy", lastCheck: "2 min ago", latency: "1.2s" },
  { name: "Weather (Open-Meteo)", status: "healthy", lastCheck: "5 min ago", latency: "340ms" },
  { name: "FIRMS (NASA)", status: "degraded", lastCheck: "12 min ago", latency: "2.1s" },
  { name: "CPCB (Government)", status: "down", lastCheck: "1 hr ago", latency: "timeout" },
];

const POLICY_VERSIONS = [
  { version: "2.1", date: "2026-07-18", status: "active", changes: "Added fingerprint fast-path" },
  { version: "2.0", date: "2026-07-15", status: "archived", changes: "Initial production policy" },
  { version: "1.0", date: "2026-07-10", status: "archived", changes: "Prototype thresholds" },
];

export default function Admin() {
  const [health, setHealth] = useState<{ status: string; version: string } | null>(null);

  useEffect(() => {
    getHealth().then(setHealth).catch(() => {});
  }, []);

  const statusColor = (s: string) =>
    s === "healthy" ? "text-emerald-400" : s === "degraded" ? "text-amber-400" : "text-red-400";

  const statusDot = (s: string) =>
    s === "healthy" ? "bg-emerald-400" : s === "degraded" ? "bg-amber-400" : "bg-red-400";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Admin</h1>
        <span className="text-xs text-gray-500 bg-gray-800 px-3 py-1 rounded">
          Service: {health?.status ?? "checking"} · v{health?.version ?? "..."}
        </span>
      </div>

      {/* Provider Health */}
      <section className="bg-gray-800 rounded-lg p-5">
        <h2 className="text-sm font-semibold text-gray-300 mb-4">Provider Health</h2>
        <div className="space-y-3">
          {MOCK_PROVIDERS.map((p) => (
            <div key={p.name} className="flex items-center gap-4 bg-gray-700/50 rounded p-3">
              <div className={`w-2 h-2 rounded-full ${statusDot(p.status)}`} />
              <span className="flex-1 text-sm font-medium">{p.name}</span>
              <span className={`text-xs ${statusColor(p.status)} capitalize`}>{p.status}</span>
              <span className="text-xs text-gray-400 w-16 text-right">{p.latency}</span>
              <span className="text-xs text-gray-500 w-20 text-right">{p.lastCheck}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Policy Versions */}
      <section className="bg-gray-800 rounded-lg p-5">
        <h2 className="text-sm font-semibold text-gray-300 mb-4">Policy Versions</h2>
        <div className="space-y-2">
          {POLICY_VERSIONS.map((p) => (
            <div key={p.version} className="flex items-center gap-4 bg-gray-700/50 rounded p-3">
              <span className="text-sm font-mono font-medium">v{p.version}</span>
              <span className="text-xs text-gray-400">{p.date}</span>
              <span className={`text-xs px-2 py-0.5 rounded ${
                p.status === "active" ? "bg-emerald-900 text-emerald-300" : "bg-gray-600 text-gray-400"
              }`}>
                {p.status}
              </span>
              <span className="text-xs text-gray-400 flex-1">{p.changes}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Calibration placeholder */}
      <section className="bg-gray-800 rounded-lg p-5">
        <h2 className="text-sm font-semibold text-gray-300 mb-4">Calibration</h2>
        <div className="grid grid-cols-3 gap-4">
          {[
            { label: "Watch Threshold", value: "0.3", range: "0.1 – 0.5" },
            { label: "Hotspot Threshold", value: "0.5", range: "0.3 – 0.7" },
            { label: "High Confidence", value: "0.7", range: "0.5 – 0.9" },
          ].map((t) => (
            <div key={t.label} className="bg-gray-700/50 rounded p-3">
              <p className="text-xs text-gray-400">{t.label}</p>
              <p className="text-lg font-bold text-white">{t.value}</p>
              <p className="text-xs text-gray-500">Range: {t.range}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Audit log placeholder */}
      <section className="bg-gray-800 rounded-lg p-5">
        <h2 className="text-sm font-semibold text-gray-300 mb-4">Recent Audit Events</h2>
        <div className="space-y-2 text-sm">
          {[
            { time: "14:32:01", event: "Signal SIG-abc123 escalated to High Confidence", user: "system" },
            { time: "14:28:15", event: "Policy v2.1 published", user: "admin" },
            { time: "14:15:42", event: "Observation obs-xyz789 submitted", user: "citizen" },
            { time: "13:58:03", event: "Provider FIRMS marked degraded", user: "system" },
          ].map((e, i) => (
            <div key={i} className="flex items-center gap-3 bg-gray-700/50 rounded p-2">
              <span className="text-xs text-gray-500 font-mono w-16">{e.time}</span>
              <span className="flex-1 text-gray-300">{e.event}</span>
              <span className="text-xs text-gray-500">{e.user}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
