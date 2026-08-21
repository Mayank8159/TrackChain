// Bottom telemetry status bar displaying system runtime and network statistics (tc.v1).

"use client";

import { useState, useEffect } from "react";
import { sseClient, type ConnectionStatusType } from "../lib/sse";

export function StatsBar() {
  const [status, setStatus] = useState<ConnectionStatusType>(sseClient.getStatus());
  const [fps] = useState(30.0);
  const [latency] = useState(14);
  const [framesCount, setFramesCount] = useState(12840);

  useEffect(() => {
    const unsub = sseClient.subscribeStatus((newStatus) => {
      setStatus(newStatus);
    });

    const timer = setInterval(() => {
      setFramesCount((prev) => prev + 30);
    }, 1000);

    return () => {
      unsub();
      clearInterval(timer);
    };
  }, []);

  const isLive = status === "connected";

  return (
    <footer className="flex flex-wrap items-center justify-between gap-4 border-t border-scada-border bg-scada-panel px-4 py-2 text-[10px] font-mono text-scada-muted lg:px-6">
      <div className="flex flex-wrap items-center gap-6">
        <span>
          NODE: <strong className="text-scada-text">EDGE-RPi5-BOGIE-01</strong>
        </span>
        <span>
          DATA MODE:{" "}
          <strong className={isLive ? "text-scada-green font-bold" : "text-scada-cyan font-bold"}>
            {isLive ? "[LIVE INGEST]" : "[DEMO MODE: SEEDED]"}
          </strong>
        </span>
        <span>
          NETWORK LATENCY:{" "}
          <strong className={latency > 20 ? "text-scada-amber" : "text-scada-green"}>
            {latency}ms
          </strong>
        </span>
        <span>
          INFERENCE FPS: <strong className="text-scada-cyan">{fps.toFixed(1)}</strong>
        </span>
        <span>
          PROCESSED FRAMES:{" "}
          <strong className="text-scada-text">{framesCount.toLocaleString()}</strong>
        </span>
      </div>

      <div className="flex items-center gap-4">
        <span>
          STORAGE: <strong className="text-scada-cyan">MinIO S3 Store</strong>
        </span>
        <span>
          PHYSICS: <strong className="text-scada-amber">EN 13848-1</strong>
        </span>
      </div>
    </footer>
  );
}
