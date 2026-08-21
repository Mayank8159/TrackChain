// Explicit Data Error State with Retry & Switch-to-DEMO Quick Actions (tc.v1).

"use client";

import React from "react";
import { AlertCircle, RefreshCw, Sparkles, ServerOff } from "lucide-react";
import { Button } from "./Button";
import { useModeStore } from "../../stores/mode-store";

export interface DataErrorProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  className?: string;
}

export function DataError({
  title = "Telemetry Data Unavailable",
  message = "Failed to communicate with the production backend API. The service may be offline or unreachable.",
  onRetry,
  className,
}: DataErrorProps) {
  const { resetToDemo } = useModeStore();

  return (
    <div
      className={`flex flex-col items-center justify-center p-8 border border-red-500/40 rounded-lg bg-slate-950/90 text-center font-mono shadow-xl ${
        className || ""
      }`}
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-500/15 border border-red-500/30 text-red-400 mb-4">
        <ServerOff size={24} />
      </div>

      <h3 className="text-base font-bold text-white uppercase tracking-wider mb-1.5">
        {title}
      </h3>

      <p className="text-xs text-scada-muted max-w-md mb-6 leading-relaxed">
        {message}
      </p>

      <div className="flex flex-wrap items-center justify-center gap-3">
        {onRetry && (
          <Button onClick={onRetry} variant="outline" size="sm" className="text-xs">
            <RefreshCw size={13} className="mr-1.5 text-cyan-400" />
            Retry Request
          </Button>
        )}

        <Button
          onClick={resetToDemo}
          variant="secondary"
          size="sm"
          className="text-xs bg-cyan-500/20 text-cyan-300 hover:bg-cyan-500/30 border border-cyan-500/50 shadow-[0_0_12px_rgba(6,182,212,0.2)]"
        >
          <Sparkles size={13} className="mr-1.5 text-cyan-400" />
          Switch to DEMO Mode
        </Button>
      </div>
    </div>
  );
}
