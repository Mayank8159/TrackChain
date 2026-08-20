// Global header with live clock and system status indicator.

"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ConnectionStatus } from "./live/ConnectionStatus";

function LiveClock() {
  const [time, setTime] = useState("");

  useEffect(() => {
    const tick = () => {
      setTime(
        new Date().toLocaleTimeString("en-IN", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          hour12: false,
        })
      );
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  return <span className="font-mono tabular-nums">{time}</span>;
}

export function Header() {
  const pathname = usePathname();

  const navLinks = [
    { href: "/", label: "Control Room" },
    { href: "/sessions", label: "Sessions" },
    { href: "/defects", label: "Defects" },
    { href: "/map", label: "GIS Map" },
    { href: "/video", label: "Telemetry & Video" },
    { href: "/reports", label: "Reports" },
    { href: "/alerts", label: "Alerts" },
  ];

  return (
    <header className="flex flex-wrap items-center justify-between gap-4 px-4 py-2.5 bg-scada-panel border-b border-scada-border">
      <div className="flex items-center gap-6">
        <Link href="/" className="flex items-center gap-3 group">
          <div className="relative flex h-8 w-8 items-center justify-center">
            <span className="absolute inline-flex h-full w-full animate-pulse rounded-full bg-scada-cyan/20" />
            <span className="relative inline-flex h-3 w-3 rounded-full bg-scada-cyan" />
          </div>
          <div>
            <h1 className="text-sm font-bold uppercase tracking-widest text-scada-text group-hover:text-scada-cyan transition-colors">
              TrackChain AI
            </h1>
            <p className="text-[9px] uppercase tracking-[0.2em] text-scada-muted">
              Integrated Track Monitoring System
            </p>
          </div>
        </Link>

        {/* Top navigation tabs */}
        <nav className="hidden lg:flex items-center gap-1">
          {navLinks.map((link) => {
            const isActive =
              link.href === "/"
                ? pathname === "/"
                : pathname.startsWith(link.href);

            return (
              <Link
                key={link.href}
                href={link.href}
                className={`px-3 py-1 rounded text-xs font-mono transition-colors ${
                  isActive
                    ? "bg-scada-cyan/15 text-scada-cyan border border-scada-cyan/30 font-bold"
                    : "text-scada-muted hover:text-scada-text hover:bg-scada-panel-header"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="flex items-center gap-4">
        <ConnectionStatus />

        <div className="hidden sm:block text-right">
          <p className="text-[9px] uppercase tracking-wider text-scada-muted">
            IST (UTC+5:30)
          </p>
          <p className="text-xs font-semibold text-scada-text">
            <LiveClock />
          </p>
        </div>
      </div>
    </header>
  );
}
