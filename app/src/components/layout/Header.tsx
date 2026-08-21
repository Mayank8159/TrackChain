// Holographic Command & Control Header — glass surface + accessibility toggle (tc.holo.v1).

"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { Menu, Search, Bell, Contrast } from "lucide-react";
import { useUIStore } from "../../stores/ui-store";
import { useAlerts } from "../../hooks/useAlerts";
import { useModeStore } from "../../stores/mode-store";
import { ModeToggle } from "../ui/ModeToggle";
import { api } from "../../lib/api";
import { cn } from "../../lib/utils";
import { useCollabStore } from "../../stores/collab-store";
import { useToast } from "../ui/Toast";
import { useRouter } from "next/navigation";

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
  const { mode, hasHydrated, connectionState, pingMs, setConnectionState, setPingMs } = useModeStore();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  // In REAL mode: Poll backend health every 10s and measure round-trip ping latency
  useEffect(() => {
    if (mode !== "REAL") return;

    const checkHealth = async () => {
      const start = performance.now();
      try {
        const healthy = await api.healthCheck();
        const latency = Math.round(performance.now() - start);
        if (healthy) {
          setPingMs(latency);
          setConnectionState("ACTIVE");
        } else {
          setPingMs(null);
          setConnectionState("ERROR");
        }
      } catch {
        setPingMs(null);
        setConnectionState("ERROR");
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 10000);
    return () => clearInterval(interval);
  }, [mode, setConnectionState, setPingMs]);

  const getStatusConfig = () => {
    if (mode === "DEMO") {
      return {
        dot: "bg-cyan-400 shadow-[0_0_8px_rgba(6,182,212,0.6)] animate-pulse",
        text: "text-cyan-300",
        label: "DIGITAL TWIN",
        subtitle: "Physics Simulation",
      };
    }

    if (connectionState === "ACTIVE") {
      return {
        dot: "bg-emerald-500 animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.6)]",
        text: "text-emerald-400",
        label: "LIVE API",
        subtitle: pingMs ? `${pingMs}ms` : "Connected",
      };
    }

    if (connectionState === "DEGRADED") {
      return {
        dot: "bg-amber-500 animate-spin",
        text: "text-amber-400",
        label: "DEGRADED",
        subtitle: "SSE Inactive",
      };
    }

    return {
      dot: "bg-red-500 animate-pulse shadow-[0_0_8px_rgba(239,68,68,0.6)]",
      text: "text-red-400",
      label: "BACKEND ERROR",
      subtitle: "Offline",
    };
  };

  if (!mounted || !hasHydrated) {
    return (
      <div className="flex items-center gap-2 rounded-control bg-slate-950/80 px-2.5 py-1 border border-scada-border/50 shadow-inner min-w-[110px]">
        <span className="h-2 w-2 rounded-full shrink-0 bg-slate-700 animate-pulse" />
        <div className="flex flex-col text-left">
          <span className="text-[10px] font-mono font-bold tracking-wider text-slate-500 leading-none">
            INITIALIZING
          </span>
          <span className="text-[8px] font-mono text-slate-600 leading-tight mt-0.5">
            Connecting...
          </span>
        </div>
      </div>
    );
  }

  const config = getStatusConfig();

  return (
    <div
      className="flex items-center gap-2 rounded-control bg-slate-950/80 px-2.5 py-1 border border-scada-border shadow-inner"
      title={`Data Source & Ingestion Status: ${config.label} (${config.subtitle})`}
    >
      <span className={cn("h-2 w-2 rounded-full shrink-0", config.dot)} />
      <div className="flex flex-col text-left">
        <span className={cn("text-[10px] font-mono font-bold tracking-wider uppercase leading-none", config.text)}>
          {config.label}
        </span>
        <span className="text-[8px] font-mono text-scada-muted leading-tight mt-0.5">
          {config.subtitle}
        </span>
      </div>
    </div>
  );
}

export function Header() {
  const { toggleMobileNav, reduceTransparency, toggleReduceTransparency } = useUIStore();
  const { alerts } = useAlerts();
  const collabStore = useCollabStore();
  const { showToast } = useToast();
  const router = useRouter();

  // Track previous annotations length to detect new ones
  const [prevAnnsLength, setPrevAnnsLength] = useState(0);

  useEffect(() => {
    if (collabStore.annotations.length > prevAnnsLength) {
      const newAnn = collabStore.annotations[collabStore.annotations.length - 1];
      if (newAnn && newAnn.author.id !== "u-me") {
        let title = "";
        let desc = newAnn.text;
        
        if (newAnn.type === "SPATIAL") title = "New Map Pin";
        else if (newAnn.type === "TEMPORAL") title = "New Video Flag";
        else title = "New Message";

        showToast({
          type: "info",
          title: `${newAnn.author.name}: ${title}`,
          description: desc,
        });
      }
      setPrevAnnsLength(collabStore.annotations.length);
    }
  }, [collabStore.annotations, prevAnnsLength, showToast]);

  const unacknowledgedCount = alerts.filter(
    (a) => !a.acknowledged && (a.severity === "critical" || a.severity === "high")
  ).length;

  return (
    <header className="sticky top-0 z-30 flex h-14 w-full items-center justify-between border-b border-white/[0.06] bg-slate-950/70 px-4 backdrop-blur-2xl">
      {/* Left Section: Mobile Menu + Wordmark */}
      <div className="flex items-center gap-3">
        <button
          onClick={toggleMobileNav}
          aria-label="Toggle navigation drawer"
          className="flex lg:hidden rounded-control p-1.5 text-slate-500 hover:bg-white/5 hover:text-slate-200 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
        >
          <Menu size={20} strokeWidth={1.5} />
        </button>

        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="relative flex h-7 w-7 items-center justify-center rounded-control bg-cyan-500/15 border border-cyan-500/40 text-cyan-400 shadow-[0_0_10px_rgba(6,182,212,0.25)] group-hover:shadow-[0_0_18px_rgba(6,182,212,0.40)] transition-all">
            <Contrast size={14} strokeWidth={1.5} />
          </div>
          <div className="flex flex-col">
            <span className="text-xs font-mono font-bold uppercase tracking-widest text-slate-200 group-hover:text-cyan-400 transition-colors">
              TrackChain AI
            </span>
            <span className="text-[9px] font-mono uppercase tracking-wider text-slate-500 -mt-0.5">
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
          className="flex w-full items-center justify-between rounded-control border border-white/[0.06] bg-white/[0.03] px-3 py-1.5 text-xs font-mono text-slate-500 hover:border-cyan-500/30 hover:text-slate-300 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
        >
          <div className="flex items-center gap-2">
            <Search size={14} strokeWidth={1.5} className="text-slate-600" />
            <span>Search chainage KM / session / defect...</span>
          </div>
          <kbd className="hidden sm:inline-block rounded bg-white/5 px-1.5 py-0.5 text-[10px] font-mono text-slate-500 border border-white/[0.06]">
            ⌘K
          </kbd>
        </button>
      </div>

      {/* Far Right Section: Live Control Cluster */}
      <div className="flex items-center gap-3">
        {/* Data Source Mode Toggle (DEMO ↔ REAL) */}
        <ModeToggle />

        {/* Connection LED & Latency */}
        <ConnectionStatusLED />

        {/* Ticking IST Clock */}
        <div className="hidden sm:flex items-center rounded-control bg-white/[0.04] px-2.5 py-1 border border-white/[0.06]">
          <TickingISTClock />
        </div>

        {/* Alert Bell Button */}
        <Link
          href="/alerts"
          aria-label={`Alert Center: ${unacknowledgedCount} unacknowledged alerts`}
          className="relative rounded-control p-1.5 text-slate-500 hover:bg-white/5 hover:text-slate-200 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
        >
          <Bell size={18} strokeWidth={1.5} />
          {unacknowledgedCount > 0 && (
            <span className="absolute -top-0.5 -right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[9px] font-mono font-bold text-white shadow-[0_0_8px_rgba(239,68,68,0.5)] animate-pulse">
              {unacknowledgedCount}
            </span>
          )}
        </Link>

        {/* Reduce Transparency Toggle (Accessibility Escape Hatch) */}
        <button
          onClick={toggleReduceTransparency}
          title={reduceTransparency ? "Disable Solid Mode (restore glass)" : "Enable Solid Mode (reduce transparency)"}
          aria-label={reduceTransparency ? "Disable Solid Mode" : "Enable Solid Mode — Reduce Transparency"}
          aria-pressed={reduceTransparency}
          className={cn(
            "flex items-center gap-1.5 rounded-control px-2 py-1 text-[10px] font-mono transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400",
            reduceTransparency
              ? "bg-cyan-500/15 text-cyan-400 border border-cyan-500/40 shadow-[0_0_8px_rgba(6,182,212,0.20)]"
              : "text-slate-500 hover:text-slate-300 hover:bg-white/5 border border-transparent"
          )}
        >
          <Contrast size={12} strokeWidth={1.5} />
          <span className="hidden lg:inline">{reduceTransparency ? "SOLID" : "GLASS"}</span>
        </button>

        {/* Global Presence Avatar Stack */}
        {collabStore.presence.length > 0 && (
          <div className="hidden lg:flex items-center pl-2 border-l border-white/[0.06]">
            {collabStore.presence.slice(0, 3).map((user, i) => (
              <div
                key={user.id}
                className={`relative -ml-2 flex h-7 w-7 items-center justify-center rounded-full border border-slate-950 text-[10px] font-bold text-white shadow-md ${user.avatarColor}`}
                style={{ zIndex: 10 - i }}
                title={`${user.name} (${user.role})`}
              >
                {user.name.charAt(0)}
              </div>
            ))}
            {collabStore.presence.length > 3 && (
              <div className="relative -ml-2 flex h-7 w-7 items-center justify-center rounded-full border border-slate-950 bg-slate-800 text-[10px] font-bold text-slate-300 shadow-md">
                +{collabStore.presence.length - 3}
              </div>
            )}
          </div>
        )}

        {/* User Badge / Operator */}
        <div
          className="flex items-center gap-2 pl-2 border-l border-white/[0.06]"
          title="Chief Track Inspector (Northern Railway)"
        >
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-cyan-600/25 border border-cyan-500/40 text-[11px] font-mono font-bold text-cyan-300">
            AE
          </div>
        </div>
      </div>
    </header>
  );
}
