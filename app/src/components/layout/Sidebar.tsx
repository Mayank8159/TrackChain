// Primary nav: dashboard, sessions, defects, map, video, reports, alerts.

"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "../../lib/utils";

interface SidebarProps {
  className?: string;
}

export function Sidebar({ className }: SidebarProps) {
  const pathname = usePathname();

  const navItems = [
    { href: "/", label: "Control Center", tag: "LIVE" },
    { href: "/sessions", label: "Inspection Runs", tag: "RUNS" },
    { href: "/defects", label: "Defect Registry", tag: "LOG" },
    { href: "/map", label: "GIS Track Map", tag: "GPS" },
    { href: "/video", label: "Synced Video & Telemetry", tag: "SYNC" },
    { href: "/reports", label: "RDSO Compliance Reports", tag: "DOC" },
    { href: "/alerts", label: "Critical Alert Center", tag: "ALARM" },
  ];

  return (
    <aside
      className={cn(
        "flex flex-col border-r border-scada-border bg-scada-panel w-64 shrink-0 font-mono",
        className
      )}
    >
      <div className="flex h-14 items-center gap-3 border-b border-scada-border px-4">
        <span className="relative flex h-3 w-3">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-scada-cyan opacity-75" />
          <span className="relative inline-flex h-3 w-3 rounded-full bg-scada-cyan" />
        </span>
        <span className="text-xs font-bold uppercase tracking-wider text-scada-text">
          TrackChain Core
        </span>
      </div>

      <nav className="flex-1 space-y-1 p-3">
        {navItems.map((item) => {
          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center justify-between rounded-lg px-3 py-2 text-xs transition-colors",
                isActive
                  ? "bg-scada-cyan/15 text-scada-cyan border border-scada-cyan/30 font-bold shadow-sm"
                  : "text-scada-muted hover:bg-scada-panel-header hover:text-scada-text"
              )}
            >
              <span>{item.label}</span>
              <span
                className={cn(
                  "text-[9px] px-1.5 py-0.5 rounded font-mono",
                  isActive
                    ? "bg-scada-cyan/20 text-scada-cyan"
                    : "bg-scada-bg text-scada-muted"
                )}
              >
                {item.tag}
              </span>
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-scada-border p-3 text-[10px] text-scada-muted">
        <p className="font-bold text-scada-text">Ministry of Railways</p>
        <p>ITMS Edge Unit v0.1.0</p>
      </div>
    </aside>
  );
}
