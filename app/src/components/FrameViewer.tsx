// Interactive canvas viewer displaying edge video frame stream with rail & sleeper line overlay (tc.v1).

"use client";

import { useState, useEffect, useCallback } from "react";
import type { LineGeometry } from "../lib/types";
import { getDeterministicLineGeometries } from "../lib/mock-provider";

interface FrameData {
  camera_id: string;
  resolution: [number, number];
  line_count: number;
  lines: LineGeometry[];
  processing_ms: number;
  timestamp: string;
}

const WIDTH = 640;
const HEIGHT = 480;

// Deterministic gravel dots coordinates for canvas texture background
const STATIC_GRAVEL_DOTS = Array.from({ length: 60 }).map((_, i) => ({
  x: ((i * 73 + 19) % WIDTH),
  y: ((i * 97 + 31) % HEIGHT),
  r: 0.8 + ((i % 3) * 0.4),
}));

function getDeterministicFrame(): FrameData {
  const lines = getDeterministicLineGeometries(WIDTH, HEIGHT);
  return {
    camera_id: "CAM-LEFT-RAIL-01",
    resolution: [WIDTH, HEIGHT],
    line_count: lines.length,
    lines,
    processing_ms: 12.4,
    timestamp: new Date().toISOString(),
  };
}

function OverlayCanvas({ lines }: { lines: LineGeometry[] }) {
  const canvasRef = useCallback(
    (canvas: HTMLCanvasElement | null) => {
      if (!canvas) return;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.clearRect(0, 0, WIDTH, HEIGHT);

      lines.forEach((l) => {
        const isRail = Math.abs(l.angle_deg) < 5 && l.length > WIDTH * 0.5;
        ctx.strokeStyle = isRail ? "#00E676" : "#00F0FF";
        ctx.lineWidth = isRail ? 2.5 : 1.5;
        ctx.globalAlpha = isRail ? 0.9 : 0.6;
        ctx.beginPath();
        ctx.moveTo(l.x1, l.y1);
        ctx.lineTo(l.x2, l.y2);
        ctx.stroke();
      });
      ctx.globalAlpha = 1;
    },
    [lines]
  );

  return (
    <canvas
      ref={canvasRef}
      width={WIDTH}
      height={HEIGHT}
      className="absolute inset-0 h-full w-full"
    />
  );
}

export function FrameViewer() {
  const [frame, setFrame] = useState<FrameData>(getDeterministicFrame);
  const [isLive, setIsLive] = useState(true);

  useEffect(() => {
    if (!isLive) return;
    const id = setInterval(() => {
      setFrame((prev) => ({
        ...prev,
        timestamp: new Date().toISOString(),
      }));
    }, 1000);
    return () => clearInterval(id);
  }, [isLive]);

  return (
    <div className="scada-card flex flex-col overflow-hidden border border-scada-border">
      {/* Toolbar */}
      <div className="flex items-center justify-between border-b border-scada-border bg-scada-panel-header px-4 py-2">
        <div className="flex items-center gap-3">
          <h2 className="text-xs font-bold uppercase tracking-wider text-scada-muted font-mono">
            Live Stream Feed
          </h2>
          <span className="badge-cyan">{frame.camera_id}</span>
          {isLive && (
            <span className="badge-green">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-scada-green" />
              FEED SYNCED
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[10px] font-mono text-scada-muted">
            {frame.resolution[0]}×{frame.resolution[1]}
          </span>
          <span className="text-[10px] font-mono text-scada-muted">
            {frame.processing_ms}ms
          </span>
          <button
            onClick={() => setIsLive(!isLive)}
            className={`rounded px-2.5 py-0.5 text-[10px] font-mono font-semibold uppercase tracking-wider transition ${
              isLive
                ? "bg-scada-red/20 text-scada-red hover:bg-scada-red/30 border border-scada-red/30"
                : "bg-scada-green/20 text-scada-green hover:bg-scada-green/30 border border-scada-green/30"
            }`}
          >
            {isLive ? "Pause" : "Resume"}
          </button>
        </div>
      </div>

      {/* Frame area */}
      <div className="relative aspect-[4/3] w-full bg-black/50 scada-grid">
        {/* Rail track grid (simulated image) */}
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          className="absolute inset-0 h-full w-full"
        >
          <defs>
            <radialGradient id="spot" cx="50%" cy="45%">
              <stop offset="0%" stopColor="#1e293b" stopOpacity="0.6" />
              <stop offset="100%" stopColor="#0B0F19" stopOpacity="1" />
            </radialGradient>
          </defs>
          <rect width={WIDTH} height={HEIGHT} fill="url(#spot)" />

          {/* Gravel texture dots (deterministic) */}
          {STATIC_GRAVEL_DOTS.map((dot, i) => (
            <circle
              key={i}
              cx={dot.x}
              cy={dot.y}
              r={dot.r}
              fill="#334155"
              opacity={0.4}
            />
          ))}
        </svg>

        {/* Detected lines overlay */}
        <OverlayCanvas lines={frame.lines} />

        {/* Crosshair */}
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <div className="h-6 w-px bg-scada-cyan/30" />
          <div className="absolute h-px w-6 bg-scada-cyan/30" />
          <div className="h-2 w-2 rounded-full border border-scada-cyan/40" />
        </div>

        {/* Corner brackets */}
        <svg className="absolute left-2 top-2 h-6 w-6 text-scada-cyan/50" viewBox="0 0 24 24">
          <path d="M0 8V0h8" fill="none" stroke="currentColor" strokeWidth="1.5" />
        </svg>
        <svg className="absolute right-2 top-2 h-6 w-6 text-scada-cyan/50" viewBox="0 0 24 24">
          <path d="M24 8V0h-8" fill="none" stroke="currentColor" strokeWidth="1.5" />
        </svg>
        <svg className="absolute bottom-2 left-2 h-6 w-6 text-scada-cyan/50" viewBox="0 0 24 24">
          <path d="M0 16v8h8" fill="none" stroke="currentColor" strokeWidth="1.5" />
        </svg>
        <svg className="absolute bottom-2 right-2 h-6 w-6 text-scada-cyan/50" viewBox="0 0 24 24">
          <path d="M24 16v8h-8" fill="none" stroke="currentColor" strokeWidth="1.5" />
        </svg>
      </div>

      {/* Footer bar */}
      <div className="flex items-center justify-between border-t border-scada-border bg-scada-panel px-4 py-2">
        <div className="flex items-center gap-4 text-[10px] font-mono text-scada-muted">
          <span>
            Lines detected:{" "}
            <span className="font-bold text-scada-cyan">{frame.lines.length}</span>
          </span>
          <span>
            Rails:{" "}
            <span className="font-bold text-scada-green">
              {frame.lines.filter((l) => Math.abs(l.angle_deg) < 5 && l.length > WIDTH * 0.5).length}
            </span>
          </span>
          <span>
            Sleepers:{" "}
            <span className="font-bold text-scada-amber">
              {frame.lines.filter((l) => Math.abs(l.angle_deg) > 40).length}
            </span>
          </span>
        </div>
        <span className="text-[10px] font-mono text-scada-muted">
          {new Date(frame.timestamp).toLocaleTimeString("en-IN")}
        </span>
      </div>
    </div>
  );
}
