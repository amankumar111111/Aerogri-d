/** Global state — minimal, one store per workflow concern. */

import { create } from "zustand";
import type { Signal, Observation } from "./types";

interface AppState {
  // Citizen reporting
  draft: {
    content: string;
    category: string;
    language: string;
    latitude: number | null;
    longitude: number | null;
    photo: File | null;
    voice: Blob | null;
  };
  setDraft: (partial: Partial<AppState["draft"]>) => void;
  resetDraft: () => void;

  // Command centre
  selectedSignalId: string | null;
  setSelectedSignal: (id: string | null) => void;

  // Signal detail
  signalDetail: Signal | null;
  setSignalDetail: (s: Signal | null) => void;

  // Observation detail
  observationDetail: Observation | null;
  setObservationDetail: (o: Observation | null) => void;
}

const defaultDraft = {
  content: "",
  category: "smoke",
  language: "en",
  latitude: null as number | null,
  longitude: null as number | null,
  photo: null as File | null,
  voice: null as Blob | null,
};

export const useStore = create<AppState>((set) => ({
  draft: { ...defaultDraft },
  setDraft: (partial) =>
    set((s) => ({ draft: { ...s.draft, ...partial } })),
  resetDraft: () => set({ draft: { ...defaultDraft } }),

  selectedSignalId: null,
  setSelectedSignal: (id) => set({ selectedSignalId: id }),

  signalDetail: null,
  setSignalDetail: (s) => set({ signalDetail: s }),

  observationDetail: null,
  setObservationDetail: (o) => set({ observationDetail: o }),
}));
