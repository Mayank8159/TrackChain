// Global Command & Control Header for TrackChain App Shell (tc.v1).

"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { Menu, Search, Bell, ShieldCheck } from "lucide-react";
import { useUIStore } from "../../stores/ui-store";
import { useAlerts } from "../../hooks/useAlerts";
import { sseClient, type ConnectionStatusType } from "../../lib/sse";
import { cn } from "../../lib/utils";

function TickingISTClock() {
  const [timeStr, setTimeStr] = useState<string>("");

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      // Format as HH:mm:ss IST
      const formatted = now.toLocaleTimeString("en-IN", {
        timeZone: "Asia/Kolkata",
        hour12: false,
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
      setTimeStr(`${formatted} IST`);
    };

    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <span className="font-mono text-xs font-semibold tabular-nums text-scada-text">
      {timeStr || "00:00:00 IST"}
    </span>
  );
}

function ConnectionStatusLED() {
  const [status, setStatus] = useState<ConnectionStatusType>(sseClient.getStatus());

  useEffect(() => {
    return sseClient.subscribeStatus((newStatus) => {
      setStatus(newStatus);
    });
  }, []);

  const config = {
    connected: {
      dot: "bg-emerald-500 animate-pulse",
      text: "text-emerald-400",
      label: "LIVE SSE",
    },
    connecting: {
      dot: "bg-amber-500 animate-spin",
      text: "text-amber-400",
      label: "CONNECTING",
    },
    disconnected: {
      dot: "bg-cyan-400",
      text: "text-cyan-400",
      label: "DEMO MODE",
    },
  }[status];

  return (
    <div
      className="flex items-center gap-2 rounded-control bg-slate-900/80 px-2.5 py-1 border border-scada-border"
      title={`Real-Time Ingestion Status: ${config.label}`}
    >
      <span className={cn("h-2 w-2 rounded-full shrink-0", config.dot)} />
      <span className={cn("text-[10px] font-mono font-bold tracking-wider uppercase", config.text)}>
        {config.label}
      </span>
    </div>
  );
}

export function Header() {
  const { toggleMobileNav } = useUIStore();
  const { alerts } = useAlerts();

  // Count unacknowledged critical & high alerts
  const unacknowledgedCount = alerts.filter(
    (a) => !a.acknowledged && (a.severity === "critical" || a.severity === "high")
  ).length;

  return (
    <header className="sticky top-0 z-30 flex h-14 w-full items-center justify-between border-b border-scada-border bg-slate-900/90 px-4 backdrop-blur-md">
      {/* Left Section: Mobile Menu + Wordmark */}
      <div className="flex items-center gap-3">
        <button
          onClick={toggleMobileNav}
          aria-label="Toggle navigation drawer"
          className="flex lg:hidden rounded-control p-1.5 text-scada-muted hover:bg-slate-800 hover:text-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-scada-accent"
        >
          <Menu size={20} />
        </button>

        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="relative flex h-7 w-7 items-center justify-center rounded-control bg-blue-600/20 border border-blue-500/40 text-blue-400">
            <ShieldCheck size={16} />
          </div>
          <div className="flex flex-col">
            <span className="text-xs font-mono font-bold uppercase tracking-widest text-scada-text group-hover:text-blue-400 transition-colors">
              TrackChain AI
            </span>
            <span className="text-[9px] font-mono uppercase tracking-wider text-scada-muted -mt-0.5">
              Northern Railway ITMS
            </span>
          </div>
        </Link>
      </div>

      {/* Center Section: Global Search Trigger */}
      <div className="hidden md:flex flex-1 max-w-md mx-6">
        <button
          type="button"
          aria-label="Quick search (Press Command+K)"
          className="flex w-full items-center justify-between rounded-control border border-scada-border bg-slate-950/60 px-3 py-1.5 text-xs font-mono text-scada-muted hover:border-slate-600 hover:text-scada-text transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-scada-accent"
        >
          <div className="flex items-center gap-2">
            <Search size={14} className="text-slate-500" />
            <span>Search chainage KM / session / defect...</span>
          </div>
          <kbd className="hidden sm:inline-block rounded bg-slate-800 px-1.5 py-0.5 text-[10px] font-mono text-slate-400 border border-slate-700">
            ⌘K
          </kbd>
        </button>
      </div>

      {/* Far Right Section: Live Control Cluster */}
      <div className="flex items-center gap-3">
        {/* Connection LED */}
        <ConnectionStatusLED />

        {/* Ticking IST Clock */}
        <div className="hidden sm:flex items-center rounded-control bg-slate-900/80 px-2.5 py-1 border border-scada-border">
          <TickingISTClock />
        </div>

        {/* Alert Bell Button */}
        <Link
          href="/alerts"
          aria-label={`Alert Center: ${unacknowledgedCount} unacknowledged alerts`}
          className="relative rounded-control p-1.5 text-scada-muted hover:bg-slate-800 hover:text-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-scada-accent"
        >
          <Bell size={18} />
          {unacknowledgedCount > 0 && (
            <span className="absolute -top-0.5 -right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[9px] font-mono font-bold text-white shadow-sm animate-pulse">
              {unacknowledgedCount}
            </span>
          )}
        </Link>

        {/* User Badge / Operator */}
        <div
          className="flex items-center gap-2 pl-2 border-l border-scada-border"
          title="Chief Track Inspector (Northern Railway)"
        >
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-blue-600/30 border border-blue-500/50 text-[11px] font-mono font-bold text-blue-300">
            AE
          </div>
        </div>
      </div>
    </header>
  );
}
