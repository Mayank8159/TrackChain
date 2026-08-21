// Holographic SCADA AppShell — dot-grid atmosphere + glass panels (tc.holo.v1).

"use client";

import React, { useEffect } from "react";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";
import { ModeBanner } from "../ui/ModeBanner";
import { useUIStore } from "../../stores/ui-store";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { toggleSidebar } = useUIStore();

  // Keyboard shortcut Ctrl+B or Cmd+B to toggle sidebar collapse
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "b") {
        e.preventDefault();
        toggleSidebar();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [toggleSidebar]);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#020617] text-slate-100">
      {/* 1. Desktop & Mobile Navigation Sidebar */}
      <Sidebar />

      {/* 2. Main Content Stack */}
      <div className="flex flex-1 flex-col overflow-hidden min-w-0">
        {/* Global Command Header */}
        <Header />

        {/* Global Mode & Connectivity Banner (DEMO / REAL ERROR) */}
        <ModeBanner />

        {/* Independently scrollable main content viewport — with holographic dot-grid */}
        <main
          id="main-content"
          tabIndex={-1}
          className="flex-1 overflow-y-auto overflow-x-hidden focus:outline-none holo-grid"
        >
          {children}
        </main>
      </div>
    </div>
  );
}
