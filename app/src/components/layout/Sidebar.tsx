// Primary Navigation Sidebar supporting desktop icon-rail collapse and mobile slide-in drawer (tc.v1).

"use client";

import React, { useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Route as RouteIcon,
  AlertTriangle,
  Map as MapIcon,
  Cpu,
  Video as VideoIcon,
  FileText,
  Siren,
  ChevronLeft,
  ChevronRight,
  X,
  Radio,
  Gauge,
  FlaskConical,
  BrainCircuit,
  Box,
} from "lucide-react";
import { useUIStore } from "../../stores/ui-store";
import { cn } from "../../lib/utils";

interface NavItem {
  href: string;
  label: string;
  tag: string;
  icon: React.ComponentType<{ size?: number | string; className?: string; strokeWidth?: number | string }>;
}

const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Control Room", tag: "LIVE", icon: LayoutDashboard },
  { href: "/digital-twin", label: "3D Digital Twin", tag: "3D", icon: Box },
  { href: "/forecast", label: "Oracle Forecast", tag: "AI", icon: BrainCircuit },
  { href: "/sessions", label: "Inspection Runs", tag: "RUNS", icon: RouteIcon },
  { href: "/defects", label: "Defect Registry", tag: "LOG", icon: AlertTriangle },
  { href: "/map", label: "GIS Track Map", tag: "GPS", icon: MapIcon },
  { href: "/lab", label: "Model Test Lab", tag: "LAB", icon: FlaskConical },
  { href: "/performance", label: "Performance", tag: "SRE", icon: Gauge },
  { href: "/devices", label: "Edge Hardware", tag: "NODE", icon: Cpu },
  { href: "/video", label: "Video & Telemetry", tag: "SYNC", icon: VideoIcon },
  { href: "/reports", label: "RDSO Reports", tag: "DOC", icon: FileText },
  { href: "/alerts", label: "Alert Center", tag: "ALARM", icon: Siren },
];

export function Sidebar() {
  const pathname = usePathname();
  const {
    isSidebarCollapsed,
    toggleSidebar,
    isMobileNavOpen,
    setMobileNavOpen,
  } = useUIStore();

  // Close mobile drawer on route change
  useEffect(() => {
    setMobileNavOpen(false);
  }, [pathname, setMobileNavOpen]);

  // Handle ESC key to close mobile drawer
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isMobileNavOpen) {
        setMobileNavOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isMobileNavOpen, setMobileNavOpen]);

  return (
    <>
      {/* ========================================================================= */}
      {/* 1. Mobile Drawer Backdrop & Slide-in Sheet (< 1024px)                     */}
      {/* ========================================================================= */}
      {isMobileNavOpen && (
        <div
          aria-hidden="true"
          onClick={() => setMobileNavOpen(false)}
          className="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm lg:hidden transition-opacity"
        />
      )}

      <aside
        aria-label="Mobile Navigation"
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-white/[0.06] glass-heavy shadow-2xl transition-transform duration-200 ease-in-out lg:hidden",
          isMobileNavOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex h-14 items-center justify-between border-b border-white/[0.06] px-4 bg-slate-950/60">
          <div className="flex items-center gap-2.5">
            <span className="relative flex h-3 w-3">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-cyan-400 opacity-60" />
              <span className="relative inline-flex h-3 w-3 rounded-full bg-cyan-500 shadow-[0_0_8px_rgba(6,182,212,0.7)]" />
            </span>
            <span className="text-xs font-mono font-bold tracking-widest text-slate-200 uppercase">
              TrackChain Core
            </span>
          </div>
          <button
            onClick={() => setMobileNavOpen(false)}
            aria-label="Close navigation menu"
            className="rounded p-1.5 text-slate-500 hover:bg-white/5 hover:text-slate-200 transition-colors"
          >
            <X size={18} strokeWidth={1.5} />
          </button>
        </div>

        <nav className="flex-1 space-y-0.5 p-3 overflow-y-auto">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive =
              item.href === "/"
                ? pathname === "/"
                : pathname ? pathname.startsWith(item.href) : false;

            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center justify-between rounded-control px-3 py-2.5 text-xs font-mono transition-all",
                  isActive
                    ? "bg-cyan-500/10 text-white font-bold border-l-2 border-cyan-400"
                    : "text-slate-400 hover:bg-white/5 hover:text-slate-200 border-l-2 border-transparent"
                )}
              >
                <div className="flex items-center gap-3">
                  <Icon
                    size={16}
                    strokeWidth={1.5}
                    className={cn(
                      "shrink-0 transition-all",
                      isActive
                        ? "text-cyan-400 drop-shadow-[0_0_6px_rgba(6,182,212,0.7)]"
                        : "text-slate-500"
                    )}
                  />
                  <span>{item.label}</span>
                </div>
                <span
                  className={cn(
                    "text-[9px] px-1.5 py-0.5 rounded font-mono",
                    isActive
                      ? "bg-cyan-500/15 text-cyan-400 border border-cyan-500/30"
                      : "bg-white/5 text-slate-500"
                  )}
                >
                  {item.tag}
                </span>
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-white/[0.06] p-3 text-[10px] font-mono text-slate-500 bg-slate-950/40">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.6)] animate-pulse" />
            <span className="font-bold text-slate-300">EDGE-01 ONLINE</span>
          </div>
          <p className="mt-1 text-slate-600">Ministry of Railways ITMS v0.1.0</p>
        </div>
      </aside>

      {/* ========================================================================= */}
      {/* 2. Desktop Collapsible Sidebar (>= 1024px)                                */}
      {/* ========================================================================= */}
      <aside
        aria-label="Desktop Navigation"
        className={cn(
          "hidden lg:flex flex-col border-r border-white/[0.06] bg-slate-950/80 backdrop-blur-2xl shrink-0 select-none transition-all duration-150 ease-in-out",
          isSidebarCollapsed ? "w-16" : "w-60"
        )}
      >
        {/* Brand / Expand Toggle Header */}
        <div className="flex h-14 items-center justify-between border-b border-white/[0.06] px-3 bg-slate-950/50">
          {!isSidebarCollapsed && (
            <div className="flex items-center gap-2.5 overflow-hidden pl-1">
              <span className="relative flex h-2.5 w-2.5 shrink-0">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-cyan-400 opacity-60" />
                <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-cyan-500 shadow-[0_0_8px_rgba(6,182,212,0.7)]" />
              </span>
              <span className="text-xs font-mono font-bold tracking-wider text-slate-200 uppercase truncate">
                TrackChain Core
              </span>
            </div>
          )}

          <button
            onClick={toggleSidebar}
            aria-label={isSidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            className={cn(
              "rounded p-1.5 text-slate-500 hover:bg-white/5 hover:text-slate-200 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400",
              isSidebarCollapsed && "mx-auto"
            )}
            title={isSidebarCollapsed ? "Expand Sidebar (Ctrl+B)" : "Collapse Sidebar"}
          >
            {isSidebarCollapsed ? <ChevronRight size={16} strokeWidth={1.5} /> : <ChevronLeft size={16} strokeWidth={1.5} />}
          </button>
        </div>

        {/* Nav links */}
        <nav className="flex-1 space-y-0.5 p-2 overflow-y-auto">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive =
              item.href === "/"
                ? pathname === "/"
                : pathname ? pathname.startsWith(item.href) : false;

            return (
              <Link
                key={item.href}
                href={item.href}
                title={isSidebarCollapsed ? item.label : undefined}
                className={cn(
                  "flex items-center rounded-control transition-all font-mono text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400",
                  isSidebarCollapsed
                    ? "justify-center h-10 w-full"
                    : "justify-between px-3 py-2",
                  isActive
                    ? "bg-cyan-500/10 text-white font-bold border-l-2 border-cyan-400"
                    : "text-slate-400 hover:bg-white/5 hover:text-slate-200 border-l-2 border-transparent"
                )}
              >
                <div className="flex items-center gap-3">
                  <Icon
                    size={16}
                    strokeWidth={1.5}
                    className={cn(
                      "shrink-0 transition-all",
                      isActive
                        ? "text-cyan-400 drop-shadow-[0_0_6px_rgba(6,182,212,0.7)]"
                        : "text-slate-500"
                    )}
                  />
                  {!isSidebarCollapsed && <span className="truncate">{item.label}</span>}
                </div>

                {!isSidebarCollapsed && (
                  <span
                    className={cn(
                      "text-[9px] px-1.5 py-0.5 rounded font-mono shrink-0",
                      isActive
                        ? "bg-cyan-500/15 text-cyan-400 border border-cyan-500/30"
                        : "bg-white/5 text-slate-500"
                    )}
                  >
                    {item.tag}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Footer Hardware Node LED */}
        <div
          className={cn(
            "border-t border-white/[0.06] p-3 text-[10px] font-mono text-slate-500 bg-slate-950/40",
            isSidebarCollapsed ? "flex justify-center" : "flex flex-col gap-1"
          )}
        >
          {isSidebarCollapsed ? (
            <div
              className="h-2.5 w-2.5 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.6)] animate-pulse"
              title="Edge Hardware Unit 01 Online"
            />
          ) : (
            <>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.6)] animate-pulse" />
                  <span className="font-bold text-slate-300">EDGE-01 ACTIVE</span>
                </div>
                <Radio size={12} strokeWidth={1.5} className="text-emerald-400" />
              </div>
              <p className="text-slate-600 text-[9px] truncate">
                RPi5 Bogie Scanner (NDLS)
              </p>
            </>
          )}
        </div>
      </aside>
    </>
  );
}
