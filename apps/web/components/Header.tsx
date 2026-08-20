"use client";

import { useState, useEffect } from "react";

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
  return (
    <header className="flex items-center justify-between px-4 py-3 lg:px-6">
      <div className="flex items-center gap-3">
        <div className="relative flex h-8 w-8 items-center justify-center">
          <span className="absolute inline-flex h-full w-full animate-pulse rounded-full bg-scada-cyan/20" />
          <span className="relative inline-flex h-3 w-3 rounded-full bg-scada-cyan" />
        </div>
        <div>
          <h1 className="text-sm font-bold uppercase tracking-widest text-scada-text">
            ITMS Control Center
          </h1>
          <p className="text-[10px] uppercase tracking-[0.2em] text-scada-muted">
            Ministry of Railways — Integrated Track Monitoring
          </p>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <span className="badge-green">
          <span className="h-1.5 w-1.5 rounded-full bg-scada-green" />
          System Online
        </span>

        <div className="hidden text-right sm:block">
          <p className="text-[10px] uppercase tracking-wider text-scada-muted">
            UTC+5:30 IST
          </p>
          <p className="text-xs font-semibold text-scada-text">
            <LiveClock />
          </p>
        </div>
      </div>
    </header>
  );
}
