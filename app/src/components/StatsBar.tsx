// Bottom telemetry status bar displaying system runtime and network statistics.

"use client";

import { useState, useEffect } from "react";

export function StatsBar() {
  const [fps, setFps] = useState(29.8);
  const [latency, setLatency] = useState(14);
  const [packets, setPackets] = useState(12840);

  useEffect(() => {
    const id = setInterval(() => {
      setFps(+(29.5 + Math.random() * 0.8).toFixed(1));
      setLatency(Math.floor(12 + Math.random() * 6));
      setPackets((p) => p + Math.floor(Math.random() * 4 + 1));
    }, 2000);
    return () => clearInterval(id);
  }, []);

  return (
    <footer className="flex flex-wrap items-center justify-between gap-4 border-t border-scada-border bg-scada-panel px-4 py-2 text-[10px] font-mono text-scada-muted lg:px-6">
      <div className="flex flex-wrap items-center gap-6">
        <span>
          NODE: <strong className="text-scada-text">EC2-AP-SOUTH-1A</strong>
        </span>
        <span>
          LATENCY:{" "}
          <strong className={latency > 20 ? "text-scada-amber" : "text-scada-green"}>
            {latency}ms
          </strong>
        </span>
        <span>
          INFERENCE FPS: <strong className="text-scada-cyan">{fps}</strong>
        </span>
        <span>
          INGESTED FRAMES:{" "}
          <strong className="text-scada-text">{packets.toLocaleString()}</strong>
        </span>
      </div>

      <div className="flex items-center gap-4">
        <span>
          STORAGE: <strong className="text-scada-cyan">MinIO S3 Connected</strong>
        </span>
        <span>
          STANDARDS: <strong className="text-scada-amber">EN 13848-1</strong>
        </span>
      </div>
    </footer>
  );
}
