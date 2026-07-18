import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { vi, describe, it, expect } from "vitest";
import Admin from "../pages/Admin";

vi.mock("../api", () => ({
  getHealth: vi.fn().mockResolvedValue({ status: "ok", version: "0.1.0" }),
}));

function renderAdmin() {
  return render(
    <BrowserRouter>
      <Admin />
    </BrowserRouter>
  );
}

describe("Admin", () => {
  it("renders admin title", () => {
    renderAdmin();
    expect(screen.getByText("Admin")).toBeInTheDocument();
  });

  it("renders provider health section", () => {
    renderAdmin();
    expect(screen.getByText("Provider Health")).toBeInTheDocument();
    expect(screen.getByText("Gemini (Interpreter)")).toBeInTheDocument();
    expect(screen.getByText("Weather (Open-Meteo)")).toBeInTheDocument();
  });

  it("renders policy versions section", () => {
    renderAdmin();
    expect(screen.getByText("Policy Versions")).toBeInTheDocument();
    expect(screen.getByText("v2.1")).toBeInTheDocument();
  });

  it("renders calibration section", () => {
    renderAdmin();
    expect(screen.getByText("Calibration")).toBeInTheDocument();
    expect(screen.getByText("Watch Threshold")).toBeInTheDocument();
  });

  it("renders audit section", () => {
    renderAdmin();
    expect(screen.getByText("Recent Audit Events")).toBeInTheDocument();
  });
});
