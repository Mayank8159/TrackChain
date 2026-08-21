import { create } from "zustand";
import type { Annotation, UserPresence } from "@trackchain/shared";

interface CollabState {
  presence: UserPresence[];
  annotations: Annotation[];
  
  setPresence: (users: UserPresence[]) => void;
  addAnnotation: (annotation: Annotation) => void;
  removeAnnotation: (id: string) => void;
  
  simulatePresence: () => void;
}

export const useCollabStore = create<CollabState>((set, get) => ({
  presence: [],
  annotations: [],

  setPresence: (users) => set({ presence: users }),

  addAnnotation: (annotation) =>
    set((state) => ({ annotations: [...state.annotations, annotation] })),

  removeAnnotation: (id) =>
    set((state) => ({
      annotations: state.annotations.filter((a) => a.id !== id),
    })),

  simulatePresence: () => {
    // Clear existing to avoid duplicates in strict mode / remounts
    set({ presence: [], annotations: [] });

    // Mock Users
    const alice: UserPresence = {
      id: "u-alice-01",
      name: "Alice (Track Engineer)",
      role: "Track Engineer",
      avatarColor: "bg-violet-500",
      status: "online",
    };

    const bob: UserPresence = {
      id: "u-bob-02",
      name: "Bob (Dispatcher)",
      role: "Dispatcher",
      avatarColor: "bg-emerald-500",
      status: "online",
    };

    set({ presence: [alice, bob] });

    // Scripted Demo Sequence
    // t+2s: Alice adds a SPATIAL pin at KM 45/8 (e.g. lat/lng)
    setTimeout(() => {
      get().addAnnotation({
        id: `ann-sp-${Date.now()}`,
        type: "SPATIAL",
        coordinates: [27.7942, 77.4325], // Somewhere near Kosi Kalan
        author: alice,
        text: "Look at the cant deficiency at KM 45/8. It's worsening.",
        mentions: [],
        created_at: Date.now(),
      });
    }, 2000);

    // t+5s: Bob adds a TEMPORAL flag at video timestamp 00:00:42
    setTimeout(() => {
      get().addAnnotation({
        id: `ann-tp-${Date.now()}`,
        type: "TEMPORAL",
        timestamp_sec: 42.0,
        author: bob,
        text: "Suspicious wear pattern here. Need a visual inspection.",
        mentions: [],
        created_at: Date.now(),
      });
    }, 5000);

    // t+8s: Alice adds a text reply mentioning @You
    setTimeout(() => {
      get().addAnnotation({
        id: `ann-in-${Date.now()}`,
        type: "INCIDENT",
        author: alice,
        text: "Agreed. @You can you authorize the tamping machine?",
        mentions: ["@You"],
        created_at: Date.now(),
      });
    }, 8000);
  },
}));
