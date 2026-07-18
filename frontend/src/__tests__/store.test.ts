import { describe, it, expect, beforeEach } from "vitest";
import { useStore } from "../store";

describe("Zustand store", () => {
  beforeEach(() => {
    useStore.setState({
      draft: {
        content: "",
        category: "smoke",
        language: "en",
        latitude: null,
        longitude: null,
        photo: null,
        voice: null,
      },
      selectedSignalId: null,
      signalDetail: null,
      observationDetail: null,
    });
  });

  it("has correct default draft", () => {
    const { draft } = useStore.getState();
    expect(draft.category).toBe("smoke");
    expect(draft.language).toBe("en");
    expect(draft.latitude).toBeNull();
  });

  it("setDraft updates partial state", () => {
    const { setDraft } = useStore.getState();
    setDraft({ category: "fire", content: "test" });
    const { draft } = useStore.getState();
    expect(draft.category).toBe("fire");
    expect(draft.content).toBe("test");
    expect(draft.language).toBe("en"); // unchanged
  });

  it("resetDraft clears all fields", () => {
    const { setDraft, resetDraft } = useStore.getState();
    setDraft({ category: "fire", content: "test", latitude: 19.0 });
    resetDraft();
    const { draft } = useStore.getState();
    expect(draft.category).toBe("smoke");
    expect(draft.content).toBe("");
    expect(draft.latitude).toBeNull();
  });

  it("setSelectedSignal updates selection", () => {
    const { setSelectedSignal } = useStore.getState();
    setSelectedSignal("signal-123");
    expect(useStore.getState().selectedSignalId).toBe("signal-123");

    setSelectedSignal(null);
    expect(useStore.getState().selectedSignalId).toBeNull();
  });
});
