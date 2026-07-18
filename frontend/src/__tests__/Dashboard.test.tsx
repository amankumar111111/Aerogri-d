import { render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { vi, describe, it, expect, beforeEach } from "vitest";
import Dashboard from "../pages/Dashboard";

// Mock the API module
vi.mock("../api", () => ({
  listSignals: vi.fn(),
  getAnalytics: vi.fn(),
  verifySignal: vi.fn(),
  archiveSignal: vi.fn(),
}));

import { listSignals, getAnalytics } from "../api";

function renderDashboard() {
  return render(
    <BrowserRouter>
      <Dashboard />
    </BrowserRouter>
  );
}

describe("Dashboard", () => {
  beforeEach(() => {
    vi.mocked(listSignals).mockResolvedValue([]);
    vi.mocked(getAnalytics).mockResolvedValue({
      total_observations: 0,
      total_signals: 0,
      active_signals: 0,
      high_confidence_signals: 0,
      avg_confidence: 0,
      signals_by_state: {},
    });
  });

  it("renders loading state initially", () => {
    renderDashboard();
    expect(screen.getByText("Loading signals...")).toBeInTheDocument();
  });

  it("renders analytics after load", async () => {
    vi.mocked(getAnalytics).mockResolvedValue({
      total_observations: 42,
      total_signals: 10,
      active_signals: 5,
      high_confidence_signals: 2,
      avg_confidence: 0.65,
      signals_by_state: { watch: 3, probable_hotspot: 2, high_confidence: 2, archived: 3 },
    });

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText("42")).toBeInTheDocument();
    });
  });

  it("renders empty state when no signals", async () => {
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText("No active signals")).toBeInTheDocument();
    });
  });

  it("renders signal feed with signals", async () => {
    vi.mocked(listSignals).mockResolvedValue([
      {
        id: "sig-1",
        state: "watch",
        latitude: 19.0,
        longitude: 72.0,
        category: "smoke",
        confidence_value: 0.45,
        contributing_observation_ids: ["obs-1"],
        contributions: [],
        environmental_context: {},
        version: 1,
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
        archived_at: null,
      },
    ]);

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText("smoke")).toBeInTheDocument();
    });
  });

  it("renders error state on API failure", async () => {
    vi.mocked(listSignals).mockRejectedValue(new Error("Network error"));

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText("Failed to load dashboard")).toBeInTheDocument();
      expect(screen.getByText("Network error")).toBeInTheDocument();
    });
  });

  it("has retry button on error", async () => {
    vi.mocked(listSignals).mockRejectedValue(new Error("fail"));

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText("Retry")).toBeInTheDocument();
    });
  });
});
