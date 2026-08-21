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
} from "lucide-react";
import { useUIStore } from "../../stores/ui-store";
import { cn } from "../../lib/utils";

interface NavItem {
  href: string;
  label: string;
  tag: string;
  icon: React.ComponentType<{ size?: number | string; className?: string }>;
}

const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Control Room", tag: "LIVE", icon: LayoutDashboard },
  { href: "/sessions", label: "Inspection Runs", tag: "RUNS", icon: RouteIcon },
  { href: "/defects", label: "Defect Registry", tag: "LOG", icon: AlertTriangle },
  { href: "/map", label: "GIS Track Map", tag: "GPS", icon: MapIcon },
  { href: "/lab", label: "Model Test Lab", tag: "AI", icon: FlaskConical },
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
          "fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-scada-border bg-slate-900 shadow-2xl transition-transform duration-200 ease-in-out lg:hidden",
          isMobileNavOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex h-14 items-center justify-between border-b border-scada-border px-4 bg-slate-900/80">
          <div className="flex items-center gap-2.5">
            <span className="relative flex h-3 w-3">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-blue-500 opacity-75" />
              <span className="relative inline-flex h-3 w-3 rounded-full bg-blue-500" />
            </span>
            <span className="text-xs font-mono font-bold tracking-widest text-scada-text uppercase">
              TrackChain Core
            </span>
          </div>
          <button
            onClick={() => setMobileNavOpen(false)}
            aria-label="Close navigation menu"
            className="rounded p-1.5 text-scada-muted hover:bg-slate-800 hover:text-white"
          >
            <X size={18} />
          </button>
        </div>

        <nav className="flex-1 space-y-1 p-3 overflow-y-auto">
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
                  "flex items-center justify-between rounded-control px-3 py-2.5 text-xs font-mono transition-colors",
                  isActive
                    ? "border-l-2 border-scada-accent bg-slate-800/80 text-white font-bold shadow-sm"
                    : "text-scada-muted hover:bg-slate-800/40 hover:text-scada-text"
                )}
              >
                <div className="flex items-center gap-3">
                  <Icon size={16} className={isActive ? "text-scada-accent" : "text-scada-muted"} />
                  <span>{item.label}</span>
                </div>
                <span
                  className={cn(
                    "text-[9px] px-1.5 py-0.5 rounded font-mono",
                    isActive
                      ? "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                      : "bg-slate-800 text-scada-muted"
                  )}
                >
                  {item.tag}
                </span>
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-scada-border p-3 text-[10px] font-mono text-scada-muted bg-slate-900/60">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="font-bold text-scada-text">EDGE-01 ONLINE</span>
          </div>
          <p className="mt-1 text-slate-500">Ministry of Railways ITMS v0.1.0</p>
        </div>
      </aside>

      {/* ========================================================================= */}
      {/* 2. Desktop Collapsible Sidebar (>= 1024px)                                */}
      {/* ========================================================================= */}
      <aside
        aria-label="Desktop Navigation"
        className={cn(
          "hidden lg:flex flex-col border-r border-scada-border bg-slate-900/95 shrink-0 select-none transition-all duration-150 ease-in-out",
          isSidebarCollapsed ? "w-16" : "w-60"
        )}
      >
        {/* Brand / Expand Toggle Header */}
        <div className="flex h-14 items-center justify-between border-b border-scada-border px-3 bg-slate-900/80">
          {!isSidebarCollapsed && (
            <div className="flex items-center gap-2.5 overflow-hidden pl-1">
              <span className="relative flex h-2.5 w-2.5 shrink-0">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-blue-500 opacity-75" />
                <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-blue-500" />
              </span>
              <span className="text-xs font-mono font-bold tracking-wider text-scada-text uppercase truncate">
                TrackChain Core
              </span>
            </div>
          )}

          <button
            onClick={toggleSidebar}
            aria-label={isSidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            className={cn(
              "rounded p-1.5 text-scada-muted hover:bg-slate-800 hover:text-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-scada-accent",
              isSidebarCollapsed && "mx-auto"
            )}
            title={isSidebarCollapsed ? "Expand Sidebar (Ctrl+B)" : "Collapse Sidebar"}
          >
            {isSidebarCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          </button>
        </div>

        {/* Nav links */}
        <nav className="flex-1 space-y-1 p-2 overflow-y-auto">
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
                  "flex items-center rounded-control transition-colors font-mono text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-scada-accent",
                  isSidebarCollapsed
                    ? "justify-center h-10 w-full"
                    : "justify-between px-3 py-2",
                  isActive
                    ? "border-l-2 border-scada-accent bg-slate-800/80 text-white font-bold shadow-sm"
                    : "text-scada-muted hover:bg-slate-800/40 hover:text-scada-text"
                )}
              >
                <div className="flex items-center gap-3">
                  <Icon
                    size={16}
                    className={cn(
                      "shrink-0",
                      isActive ? "text-scada-accent" : "text-scada-muted"
                    )}
                  />
                  {!isSidebarCollapsed && <span className="truncate">{item.label}</span>}
                </div>

                {!isSidebarCollapsed && (
                  <span
                    className={cn(
                      "text-[9px] px-1.5 py-0.5 rounded font-mono shrink-0",
                      isActive
                        ? "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                        : "bg-slate-800 text-scada-muted"
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
            "border-t border-scada-border p-3 text-[10px] font-mono text-scada-muted bg-slate-900/60",
            isSidebarCollapsed ? "flex justify-center" : "flex flex-col gap-1"
          )}
        >
          {isSidebarCollapsed ? (
            <div
              className="h-2.5 w-2.5 rounded-full bg-emerald-500 animate-pulse"
              title="Edge Hardware Unit 01 Online"
            />
          ) : (
            <>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                  <span className="font-bold text-scada-text">EDGE-01 ACTIVE</span>
                </div>
                <Radio size={12} className="text-emerald-400" />
              </div>
              <p className="text-slate-500 text-[9px] truncate">
                RPi5 Bogie Scanner (NDLS)
              </p>
            </>
          )}
        </div>
      </aside>
    </>
  );
}
