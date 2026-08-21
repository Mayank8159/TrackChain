// Global UI state store for TrackChain App Shell navigation, sidebar & accessibility (tc.holo.v1).

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

interface UIState {
  isSidebarCollapsed: boolean;
  isMobileNavOpen: boolean;
  reduceTransparency: boolean;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  toggleMobileNav: () => void;
  setMobileNavOpen: (open: boolean) => void;
  toggleReduceTransparency: () => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set, get) => ({
      isSidebarCollapsed: false,
      isMobileNavOpen: false,
      reduceTransparency: false,
      toggleSidebar: () =>
        set((state) => ({ isSidebarCollapsed: !state.isSidebarCollapsed })),
      setSidebarCollapsed: (collapsed) => set({ isSidebarCollapsed: collapsed }),
      toggleMobileNav: () =>
        set((state) => ({ isMobileNavOpen: !state.isMobileNavOpen })),
      setMobileNavOpen: (open) => set({ isMobileNavOpen: open }),
      toggleReduceTransparency: () => {
        const next = !get().reduceTransparency;
        set({ reduceTransparency: next });
        // Apply or remove the solid-mode data attribute on <html>
        if (typeof document !== "undefined") {
          if (next) {
            document.documentElement.setAttribute("data-theme", "solid");
          } else {
            document.documentElement.removeAttribute("data-theme");
          }
        }
      },
    }),
    {
      name: "trackchain_ui_preferences",
      storage: createJSONStorage(() =>
        typeof window !== "undefined"
          ? localStorage
          : {
              getItem: () => null,
              setItem: () => {},
              removeItem: () => {},
            }
      ),
      partialize: (state) => ({
        isSidebarCollapsed: state.isSidebarCollapsed,
        reduceTransparency: state.reduceTransparency,
      }),
      onRehydrateStorage: () => (state) => {
        // Re-apply data-theme on page reload if preference was persisted
        if (state?.reduceTransparency && typeof document !== "undefined") {
          document.documentElement.setAttribute("data-theme", "solid");
        }
      },
    }
  )
);
