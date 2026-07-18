/** AEROGRID API client — typed, minimal, no frameworks. */

import type {
  AnalyticsSummary,
  HeatmapPoint,
  HealthResponse,
  Observation,
  ObservationSubmitRequest,
  ObservationSubmitResponse,
  Signal,
  TimelineEntry,
} from "./types";

const BASE = "/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-Correlation-ID": crypto.randomUUID(),
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.error?.message ?? `HTTP ${res.status}`);
  }
  return res.json();
}

// --- Observations ---

export async function submitObservation(
  data: ObservationSubmitRequest
): Promise<ObservationSubmitResponse> {
  return request("/observations", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getObservation(id: string): Promise<Observation> {
  return request(`/observations/${id}`);
}

// --- Signals ---

export async function listSignals(params?: {
  state?: string;
  offset?: number;
  limit?: number;
}): Promise<Signal[]> {
  const qs = new URLSearchParams();
  if (params?.state) qs.set("state", params.state);
  if (params?.offset) qs.set("offset", String(params.offset));
  if (params?.limit) qs.set("limit", String(params.limit));
  const q = qs.toString();
  return request(`/signals${q ? `?${q}` : ""}`);
}

export async function getSignal(id: string): Promise<Signal> {
  return request(`/signals/${id}`);
}

export async function verifySignal(id: string) {
  return request<{ signal_id: string; state: string; message: string }>(
    `/signals/${id}/verify`,
    { method: "POST" }
  );
}

export async function archiveSignal(id: string) {
  return request<{ signal_id: string; state: string; message: string }>(
    `/signals/${id}/archive`,
    { method: "POST" }
  );
}

// --- Analytics ---

export async function getAnalytics(): Promise<AnalyticsSummary> {
  return request("/analytics");
}

export async function getHeatmap(): Promise<HeatmapPoint[]> {
  return request("/analytics/heatmap");
}

export async function getTimeline(): Promise<TimelineEntry[]> {
  return request("/analytics/timeline");
}

// --- Health ---

export async function getHealth(): Promise<HealthResponse> {
  return request("/health");
}
