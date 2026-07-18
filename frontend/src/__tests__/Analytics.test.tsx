import { render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { vi, describe, it, expect, beforeEach } from "vitest";
import Analytics from "../pages/Analytics";

vi.mock("../api", () => ({
  getAnalytics: vi.fn(),
  getHeatmap: vi.fn(),
  getTimeline: vi.fn(),
}));

import { getAnalytics, getHeatmap, getTimeline } from "../api";

describe("Analytics", () => {
  beforeEach(() => {
    vi.mocked(getAnalytics).mockResolvedValue({
      total_observations: 150,
      total_signals: 25,
      active_signals: 12,
      high_confidence_signals: 5,
      avg_confidence: 0.68,
      signals_by_state: { watch: 5, probable_hotspot: 4, high_confidence: 3, archived: 13 },
    });
    vi.mocked(getHeatmap).mockResolvedValue([]);
    vi.mocked(getTimeline).mockResolvedValue([]);
  });

  function renderAnalytics() {
    return render(
      <BrowserRouter>
        <Analytics />
      </BrowserRouter>
    );
  }

  it("renders loading state", () => {
    renderAnalytics();
    expect(screen.getByText("Loading analytics...")).toBeInTheDocument();
  });

  it("renders summary cards after load", async () => {
    renderAnalytics();

    await waitFor(() => {
      expect(screen.getByText("150")).toBeInTheDocument();
      expect(screen.getByText("25")).toBeInTheDocument();
      expect(screen.getByText("12")).toBeInTheDocument();
    });
  });

  it("renders signal state distribution", async () => {
    renderAnalytics();

    await waitFor(() => {
      expect(screen.getByText("Signals by State")).toBeInTheDocument();
    });
    expect(screen.getByText("watch")).toBeInTheDocument();
    expect(screen.getByText("high confidence")).toBeInTheDocument();
  });

  it("renders recent activity section", async () => {
    renderAnalytics();

    await waitFor(() => {
      expect(screen.getByText("Recent Activity")).toBeInTheDocument();
    });
  });

  it("renders heatmap section", async () => {
    renderAnalytics();

    await waitFor(() => {
      expect(screen.getByText("Signal Heatmap")).toBeInTheDocument();
    });
  });
});
