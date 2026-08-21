// Live/offline/reconnecting indicator for the real-time feed with transparent demo indicator (tc.v1).

"use client";

import React, { useState, useEffect } from "react";
import { sseClient, type ConnectionStatusType } from "../../lib/sse";
import { cn } from "../../lib/utils";

export function ConnectionStatus({ className }: { className?: string }) {
  const [status, setStatus] = useState<ConnectionStatusType>(sseClient.getStatus());

  useEffect(() => {
    return sseClient.subscribeStatus((newStatus) => {
      setStatus(newStatus);
    });
  }, []);

  const config = {
    connected: {
      label: "LIVE SSE FEED ACTIVE",
      dot: "bg-scada-green animate-pulse",
      text: "text-scada-green",
      bg: "bg-scada-green/10 border-scada-green/30",
    },
    connecting: {
      label: "CONNECTING TO SSE...",
      dot: "bg-scada-amber animate-spin",
      text: "text-scada-amber",
      bg: "bg-scada-amber/10 border-scada-amber/30",
    },
    disconnected: {
      label: "DEMO MODE (SEEDED)",
      dot: "bg-scada-cyan",
      text: "text-scada-cyan",
      bg: "bg-scada-cyan/10 border-scada-cyan/30",
    },
  }[status];

  return (
    <div
      className={cn(
        "inline-flex items-center gap-2 rounded-full border px-2.5 py-0.5 text-[10px] font-mono font-medium",
        config.bg,
        config.text,
        className
      )}
      title={
        status === "connected"
          ? "Connected to FastAPI Server-Sent Events stream (/api/alerts/stream)"
          : "Operating in transparent offline demo mode with deterministic seeded telemetry"
      }
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", config.dot)} />
      <span>{config.label}</span>
    </div>
  );
}
