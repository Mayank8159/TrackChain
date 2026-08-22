// Persistent Global Data Source Mode Banner for TrackChain App Shell (tc.v1).

"use client";

import React from "react";
import { AlertTriangle, Sparkles, RefreshCw, ServerOff, WifiOff } from "lucide-react";
import { useModeStore } from "../../stores/mode-store";
import { env } from "../../lib/env";
import { Button } from "./Button";

export function ModeBanner() {
  const { mode, connectionState, resetToDemo, setMode } = useModeStore();

  // 1. DEMO Mode Banner
  if (mode === "DEMO") {
    return (
      <div className="w-full bg-cyan-950/40 border-b border-cyan-500/30 px-4 py-1.5 backdrop-blur-sm">
        <div className="flex flex-wrap items-center justify-center gap-2 text-xs font-mono">
          <Sparkles className="w-3.5 h-3.5 text-cyan-400 shrink-0 animate-pulse" />
          <span className="text-cyan-300 font-bold tracking-wider uppercase">
            LOCAL DIGITAL TWIN — PHYSICS-SEEDED SIMULATION DATA
          </span>
          <span className="text-cyan-400/70 text-[11px]">
            (10km EN 13848-1 Kinematic Model · Real TimescaleDB & IsolationForest Anomaly Engine)
          </span>
        </div>
      </div>
    );
  }

  // 2. REAL Mode Backend Unreachable Error Banner
  if (mode === "REAL" && connectionState === "ERROR") {
    return (
      <div className="w-full bg-red-950/70 border-b border-red-500/40 px-4 py-2 backdrop-blur-sm">
        <div className="flex flex-wrap items-center justify-between gap-3 max-w-7xl mx-auto text-xs font-mono">
          <div className="flex items-center gap-2">
            <ServerOff className="w-4 h-4 text-red-400 shrink-0 animate-pulse" />
            <span className="text-red-300 font-bold uppercase tracking-wider">
              REAL MODE ERROR: BACKEND UNREACHABLE
            </span>
            <span className="text-red-300/80 text-[11px] hidden sm:inline">
              FastAPI server is not responding at {env.apiUrl}.
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setMode("REAL")}
              className="px-2.5 py-1 text-[11px] font-mono bg-slate-900 hover:bg-slate-800 rounded border border-scada-border text-white transition-colors"
            >
              <RefreshCw size={11} className="inline mr-1 text-slate-400" />
              Retry Connection
            </button>

            <button
              onClick={resetToDemo}
              className="px-3 py-1 text-[11px] font-mono bg-cyan-500/20 hover:bg-cyan-500/30 rounded border border-cyan-500/50 text-cyan-300 font-bold transition-all shadow-[0_0_10px_rgba(6,182,212,0.2)]"
            >
              Switch to DEMO
            </button>
          </div>
        </div>
      </div>
    );
  }

  // 3. REAL Mode Degraded SSE Banner
  if (mode === "REAL" && connectionState === "DEGRADED") {
    return (
      <div className="w-full bg-amber-950/40 border-b border-amber-500/30 px-4 py-1.5 backdrop-blur-sm">
        <div className="flex flex-wrap items-center justify-center gap-2 text-xs font-mono">
          <WifiOff className="w-3.5 h-3.5 text-amber-400 shrink-0" />
          <span className="text-amber-300 font-bold tracking-wider uppercase">
            STREAM DEGRADED — SSE DISCONNECTED
          </span>
          <span className="text-amber-400/70 text-[11px]">
            (REST API online · Live push telemetry stream reconnecting)
          </span>
        </div>
      </div>
    );
  }

  return null;
}
