"use client";

import { useState, useEffect } from "react";

function useCountUp(target: number, duration = 800) {
  const [value, setValue] = useState(0);
  useEffect(() => {
    const start = performance.now();
    const from = value;
    const step = (now: number) => {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(Math.round(from + (target - from) * eased));
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [target]);
  return value;
}

export function StatsBar() {
  const [uptime, setUptime] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setUptime((u) => u + 1), 1000);
    return () => clearInterval(id);
  }, []);

  const hrs = Math.floor(uptime / 3600);
  const mins = Math.floor((uptime % 36060) / 60);
  const secs = uptime % 60;
  const uptimeStr = `${String(hrs).padStart(2, "0")}:${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;

  const framesProcessed = useCountUp(12847, 1200);
  const avgLatency = useCountUp(11, 600);

  const stats = [
    { label: "Active Cameras", value: "3", accent: "text-scada-cyan" },
    { label: "Frames Processed", value: framesProcessed.toLocaleString(), accent: "text-scada-blue" },
    { label: "Avg Latency", value: `${avgLatency}ms`, accent: "text-scada-green" },
    { label: "System Uptime", value: uptimeStr, accent: "text-scada-amber" },
  ];

  return (
    <footer className="px-4 py-3 lg:px-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        {stats.map((s) => (
          <div key={s.label} className="flex items-center gap-2">
            <span className="text-[10px] uppercase tracking-wider text-scada-muted">
              {s.label}:
            </span>
            <span className={`text-xs font-bold tabular-nums ${s.accent}`}>
              {s.value}
            </span>
          </div>
        ))}
        <span className="text-[10px] text-scada-muted">
          ITMS v0.1.0 — Phase 3
        </span>
      </div>
    </footer>
  );
}
