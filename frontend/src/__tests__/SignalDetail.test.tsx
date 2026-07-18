import { render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter, MemoryRouter, Route, Routes } from "react-router-dom";
import { vi, describe, it, expect, beforeEach } from "vitest";
import SignalDetail from "../pages/SignalDetail";

vi.mock("../api", () => ({
  getSignal: vi.fn(),
  getObservation: vi.fn(),
}));

import { getSignal, getObservation } from "../api";

const mockSignal = {
  id: "sig-1",
  state: "probable_hotspot",
  latitude: 19.076,
  longitude: 72.878,
  category: "smoke",
  confidence_value: 0.72,
  contributing_observation_ids: ["obs-1", "obs-2"],
  contributions: [
    {
      observation_id: "obs-1",
      fingerprint: "abc",
      dimension_scores: { semantic: 0.82, spatial: 0.91, temporal: 0.77, independence: 1.0, environmental: 0.42 },
      contribution_score: 0.79,
      weighted_contribution: 0.55,
      evaluation_timestamp: "2024-01-01T00:00:00Z",
    },
  ],
  environmental_context: { temperature: 38, humidity: 35 },
  version: 3,
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T01:00:00Z",
  archived_at: null,
};

function renderSignalDetail(signalId = "sig-1") {
  return render(
    <MemoryRouter initialEntries={[`/signals/${signalId}`]}>
      <Routes>
        <Route path="/signals/:id" element={<SignalDetail />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("SignalDetail", () => {
  beforeEach(() => {
    vi.mocked(getSignal).mockResolvedValue(mockSignal);
    vi.mocked(getObservation).mockResolvedValue({
      id: "obs-1",
      content: "Heavy smoke",
      category: "smoke",
      status: "interpreted",
      created_at: "2024-01-01T00:00:00Z",
    });
  });

  it("shows loading state", () => {
    renderSignalDetail();
    expect(screen.getByText("Loading signal...")).toBeInTheDocument();
  });

  it("renders signal detail after load", async () => {
    renderSignalDetail();

    await waitFor(() => {
      expect(screen.getByText("smoke")).toBeInTheDocument();
    });
    expect(screen.getByText("Probable Hotspot")).toBeInTheDocument();
  });

  it("shows evidence convergence dimensions", async () => {
    renderSignalDetail();

    await waitFor(() => {
      expect(screen.getByText("Evidence Convergence")).toBeInTheDocument();
    });
    expect(screen.getByText("Semantic Match")).toBeInTheDocument();
    expect(screen.getByText("Spatial Proximity")).toBeInTheDocument();
    expect(screen.getByText("Temporal Proximity")).toBeInTheDocument();
  });

  it("shows environmental context data", async () => {
    renderSignalDetail();

    await waitFor(() => {
      expect(screen.getByText("temperature")).toBeInTheDocument();
    });
    expect(screen.getByText("38")).toBeInTheDocument();
    expect(screen.getByText("humidity")).toBeInTheDocument();
    expect(screen.getByText("35")).toBeInTheDocument();
  });

  it("shows signal info", async () => {
    renderSignalDetail();

    await waitFor(() => {
      expect(screen.getByText("Signal Info")).toBeInTheDocument();
    });
    expect(screen.getByText("Version")).toBeInTheDocument();
    expect(screen.getByText("v3")).toBeInTheDocument();
  });

  it("shows error state on failure", async () => {
    vi.mocked(getSignal).mockRejectedValue(new Error("Not found"));

    renderSignalDetail();

    await waitFor(() => {
      expect(screen.getByText("Not found")).toBeInTheDocument();
    });
  });
});
