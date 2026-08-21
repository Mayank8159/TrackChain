// Explicit Data Source Mode Toggle (DEMO ↔ REAL) with loading feedback (tc.v1).

"use client";

import React, { useState, useEffect } from "react";
import { CheckCircle2, Loader2, Radio, Server, Sparkles } from "lucide-react";
import { useModeStore, type AppMode } from "../../stores/mode-store";
import { cn } from "../../lib/utils";

export function ModeToggle() {
  const { mode, hasHydrated, connectionState, setMode } = useModeStore();
  const [mounted, setMounted] = useState(false);
  const [isSwitching, setIsSwitching] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const handleToggle = async (newMode: AppMode) => {
    if (newMode === mode || isSwitching) return;
    setIsSwitching(true);
    try {
      await setMode(newMode);
    } finally {
      setIsSwitching(false);
    }
  };

  const isDemo = (!mounted || !hasHydrated) ? true : mode === "DEMO";

  return (
    <div
      className="flex items-center gap-1.5 rounded-lg border border-scada-border bg-slate-950/80 p-1 shadow-inner"
      role="group"
      aria-label="Data Source Mode Selection"
    >
      {/* DEMO Mode Button */}
      <button
        type="button"
        onClick={() => handleToggle("DEMO")}
        disabled={isSwitching}
        aria-pressed={isDemo}
        className={cn(
          "flex items-center gap-1.5 rounded px-2.5 py-1 text-xs font-mono font-bold transition-all",
          isDemo
            ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/40 shadow-[0_0_12px_rgba(6,182,212,0.25)]"
            : "text-scada-muted hover:text-white hover:bg-slate-900 border border-transparent"
        )}
        title="DEMO Mode: Deterministic local simulation data (Zero network calls)"
      >
        {isDemo ? (
          <CheckCircle2 size={12} className="text-cyan-400" />
        ) : (
          <Sparkles size={12} className="text-slate-500" />
        )}
        <span>DEMO</span>
      </button>

      {/* REAL Mode Button */}
      <button
        type="button"
        onClick={() => handleToggle("REAL")}
        disabled={isSwitching}
        aria-pressed={!isDemo}
        className={cn(
          "flex items-center gap-1.5 rounded px-2.5 py-1 text-xs font-mono font-bold transition-all",
          !isDemo
            ? connectionState === "ERROR"
              ? "bg-red-500/20 text-red-400 border border-red-500/40 shadow-[0_0_12px_rgba(239,68,68,0.25)]"
              : "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 shadow-[0_0_12px_rgba(16,185,129,0.25)]"
            : "text-scada-muted hover:text-white hover:bg-slate-900 border border-transparent"
        )}
        title="REAL Mode: Live FastAPI backend REST and SSE streaming telemetry"
      >
        {isSwitching ? (
          <Loader2 size={12} className="animate-spin text-emerald-400" />
        ) : !isDemo ? (
          <Radio size={12} className="animate-pulse text-emerald-400" />
        ) : (
          <Server size={12} className="text-slate-500" />
        )}
        <span>REAL</span>
      </button>
    </div>
  );
}
