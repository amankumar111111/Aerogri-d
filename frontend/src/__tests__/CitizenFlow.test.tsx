import { render, screen, fireEvent } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { vi, describe, it, expect } from "vitest";
import CitizenFlow from "../pages/CitizenFlow";

vi.mock("../api", () => ({
  submitObservation: vi.fn(),
}));

function renderCitizenFlow() {
  return render(
    <BrowserRouter>
      <CitizenFlow />
    </BrowserRouter>
  );
}

describe("CitizenFlow", () => {
  it("renders the first step (photo capture)", () => {
    renderCitizenFlow();
    expect(screen.getByText("Capture Evidence")).toBeInTheDocument();
    expect(screen.getByText("Take a photo of what you observe")).toBeInTheDocument();
  });

  it("renders language selector", () => {
    renderCitizenFlow();
    expect(screen.getByText("English")).toBeInTheDocument();
    expect(screen.getByText("हिन्दी")).toBeInTheDocument();
    expect(screen.getByText("मराठी")).toBeInTheDocument();
  });

  it("has skip photo button", () => {
    renderCitizenFlow();
    expect(screen.getByText("Skip photo →")).toBeInTheDocument();
  });

  it("progress bar shows 5 steps", () => {
    renderCitizenFlow();
    // 5 step indicators in the progress bar
    const progressBars = document.querySelectorAll(".h-1");
    expect(progressBars.length).toBe(5);
  });

  it("can switch language", () => {
    renderCitizenFlow();
    const hindiBtn = screen.getByText("हिन्दी");
    fireEvent.click(hindiBtn);
    // Hindi button should now be active (bg-emerald-600)
    expect(hindiBtn.className).toContain("bg-emerald-600");
  });

  it("skip photo moves to voice step", () => {
    renderCitizenFlow();
    fireEvent.click(screen.getByText("Skip photo →"));
    expect(screen.getByText("Record Voice Note")).toBeInTheDocument();
  });

  it("skip voice moves to text step", () => {
    renderCitizenFlow();
    fireEvent.click(screen.getByText("Skip photo →"));
    fireEvent.click(screen.getByText("Skip →"));
    expect(screen.getByText("Describe What You See")).toBeInTheDocument();
  });
});
