// Live/offline/reconnecting indicator for the realtime feed.

"use client";

import React, { useState, useEffect } from "react";
import { realtimeClient } from "../../lib/websocket";
import { cn } from "../../lib/utils";

export function ConnectionStatus({ className }: { className?: string }) {
  const [status, setStatus] = useState<"connected" | "connecting" | "disconnected">("connected");

  useEffect(() => {
    return realtimeClient.subscribeStatus((newStatus) => {
      setStatus(newStatus);
    });
  }, []);

  const config = {
    connected: {
      label: "LIVE FEED ACTIVE",
      dot: "bg-scada-green animate-pulse",
      text: "text-scada-green",
      bg: "bg-scada-green/10 border-scada-green/30",
    },
    connecting: {
      label: "CONNECTING...",
      dot: "bg-scada-amber animate-spin",
      text: "text-scada-amber",
      bg: "bg-scada-amber/10 border-scada-amber/30",
    },
    disconnected: {
      label: "STREAM SIMULATED",
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
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", config.dot)} />
      <span>{config.label}</span>
    </div>
  );
}
