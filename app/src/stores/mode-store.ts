// Centralized Mode & Connection State Machine Store for TrackChain (tc.v1).
// Governs DEMO (Deterministic Simulation) vs REAL (Production Backend & Live SSE) modes.

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { api } from "../lib/api";

export type AppMode = "DEMO" | "REAL";
export type ConnectionState = "ACTIVE" | "DEGRADED" | "ERROR" | "SWITCHING";

interface ModeState {
  mode: AppMode;
  hasHydrated: boolean;
  connectionState: ConnectionState;
  lastModeChange: number;
  pingMs: number | null;

  // Actions
  setMode: (targetMode: AppMode) => Promise<void>;
  setConnectionState: (state: ConnectionState) => void;
  setPingMs: (ping: number | null) => void;
  setHasHydrated: (state: boolean) => void;
  resetToDemo: () => void;

  // Selectors / helpers
  isDemo: () => boolean;
  isReal: () => boolean;
  isHealthy: () => boolean;
}

export const useModeStore = create<ModeState>()(
  persist(
    (set, get) => ({
      mode: "DEMO", // Safe default state: deterministic simulation
      hasHydrated: false,
      connectionState: "ACTIVE",
      lastModeChange: 0,
      pingMs: null,

      setHasHydrated: (state: boolean) => set({ hasHydrated: state }),

      setMode: async (targetMode: AppMode) => {
        const now = Date.now();
        // Debounce protection: enforce minimum 500ms between mode changes
        if (now - get().lastModeChange < 500) {
          return;
        }

        if (targetMode === get().mode) {
          return;
        }

        if (targetMode === "DEMO") {
          set({
            mode: "DEMO",
            connectionState: "ACTIVE",
            lastModeChange: now,
            pingMs: null,
          });
          return;
        }

        // Target is REAL mode: verify backend health atomically before transitioning
        set({
          connectionState: "SWITCHING",
          lastModeChange: now,
        });

        try {
          const startTime = performance.now();
          const isHealthy = await api.healthCheck();
          const latency = Math.round(performance.now() - startTime);

          if (isHealthy) {
            set({
              mode: "REAL",
              connectionState: "ACTIVE",
              pingMs: latency,
            });
          } else {
            set({
              mode: "REAL",
              connectionState: "ERROR",
              pingMs: null,
            });
          }
        } catch {
          set({
            mode: "REAL",
            connectionState: "ERROR",
            pingMs: null,
          });
        }
      },

      setConnectionState: (state: ConnectionState) => {
        set({ connectionState: state });
      },

      setPingMs: (ping: number | null) => {
        set({ pingMs: ping });
      },

      resetToDemo: () => {
        set({
          mode: "DEMO",
          connectionState: "ACTIVE",
          lastModeChange: Date.now(),
          pingMs: null,
        });
      },

      isDemo: () => get().mode === "DEMO",
      isReal: () => get().mode === "REAL",
      isHealthy: () => get().connectionState === "ACTIVE",
    }),
    {
      name: "trackchain-mode",
      storage: createJSONStorage(() =>
        typeof window !== "undefined"
          ? localStorage
          : {
              getItem: () => null,
              setItem: () => {},
              removeItem: () => {},
            }
      ),
      partialize: (state) => ({ mode: state.mode }), // Only persist mode, not transient connection states
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    }
  )
);
