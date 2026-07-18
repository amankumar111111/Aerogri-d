import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

// We need to dynamically import after mocking
describe("API client", () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it("submitObservation sends correct request", async () => {
    const { submitObservation } = await import("../api");

    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        observation_id: "test-id",
        fingerprint: "abc123",
        status: "submitted",
        tracking_ref: "test-id",
      }),
    });

    const result = await submitObservation({
      content: "smoke visible",
      latitude: 19.0,
      longitude: 72.0,
      category: "smoke",
      device_id: "test-device",
    });

    expect(mockFetch).toHaveBeenCalledOnce();
    expect(result.observation_id).toBe("test-id");
    expect(result.status).toBe("submitted");
  });

  it("listSignals sends correct request", async () => {
    const { listSignals } = await import("../api");

    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve([]),
    });

    const result = await listSignals({ state: "watch", limit: 10 });

    expect(mockFetch).toHaveBeenCalledOnce();
    expect(result).toEqual([]);
  });

  it("getSignal sends correct request", async () => {
    const { getSignal } = await import("../api");

    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: "test", state: "watch" }),
    });

    const result = await getSignal("test-id");
    expect(result.id).toBe("test");
  });

  it("throws on non-OK response", async () => {
    const { submitObservation } = await import("../api");

    mockFetch.mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ error: { message: "Bad request" } }),
    });

    await expect(
      submitObservation({
        content: "test",
        latitude: 19.0,
        longitude: 72.0,
        category: "smoke",
        device_id: "test",
      })
    ).rejects.toThrow("Bad request");
  });
});
