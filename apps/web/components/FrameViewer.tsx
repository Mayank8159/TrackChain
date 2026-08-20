"use client";

import { useState, useEffect, useCallback } from "react";

interface LineGeometry {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  angle_deg: number;
  length: number;
}

interface FrameData {
  camera_id: string;
  resolution: [number, number];
  line_count: number;
  lines: LineGeometry[];
  processing_ms: number;
  timestamp: string;
}

const MOCK_CAMERAS = ["CAM-SECTOR-A1", "CAM-SECTOR-B3", "CAM-SECTOR-C2"];
const WIDTH = 640;
const HEIGHT = 480;

function generateMockLines(): LineGeometry[] {
  const lines: LineGeometry[] = [];
  const railY1 = 180 + Math.random() * 10 - 5;
  const railY2 = 300 + Math.random() * 10 - 5;

  lines.push({
    x1: 20,
    y1: railY1,
    x2: WIDTH - 20,
    y2: railY1 + (Math.random() * 4 - 2),
    angle_deg: +(Math.random() * 2 - 1).toFixed(2),
    length: +(WIDTH - 40 + Math.random() * 10).toFixed(2),
  });
  lines.push({
    x1: 20,
    y1: railY2,
    x2: WIDTH - 20,
    y2: railY2 + (Math.random() * 4 - 2),
    angle_deg: +(Math.random() * 2 - 1).toFixed(2),
    length: +(WIDTH - 40 + Math.random() * 10).toFixed(2),
  });

  const sleeperCount = 8 + Math.floor(Math.random() * 4);
  for (let i = 0; i < sleeperCount; i++) {
    const x = 60 + (i * (WIDTH - 120)) / (sleeperCount - 1) + Math.random() * 8 - 4;
    lines.push({
      x1: x,
      y1: railY1 + 10,
      x2: x + (Math.random() * 6 - 3),
      y2: railY2 - 10,
      angle_deg: +(85 + Math.random() * 10).toFixed(2),
      length: +(railY2 - railY1 - 20 + Math.random() * 10).toFixed(2),
    });
  }
  return lines;
}

function mockFrame(): FrameData {
  return {
    camera_id: MOCK_CAMERAS[Math.floor(Math.random() * MOCK_CAMERAS.length)],
    resolution: [WIDTH, HEIGHT],
    line_count: 0,
    lines: generateMockLines(),
    processing_ms: +(8 + Math.random() * 15).toFixed(2),
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
        const isRail =
          Math.abs(l.angle_deg) < 5 && l.length > WIDTH * 0.5;
        ctx.strokeStyle = isRail ? "#06d6a0" : "#3b82f6";
        ctx.lineWidth = isRail ? 2 : 1;
        ctx.globalAlpha = isRail ? 0.9 : 0.5;
        ctx.beginPath();
        ctx.moveTo(l.x1, l.y1);
        ctx.lineTo(l.x2, l.y2);
        ctx.stroke();
      });
      ctx.globalAlpha = 1;
    },
    [lines],
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
  const [frame, setFrame] = useState<FrameData>(mockFrame);
  const [isLive, setIsLive] = useState(true);

  useEffect(() => {
    if (!isLive) return;
    const id = setInterval(() => setFrame(mockFrame()), 1200);
    return () => clearInterval(id);
  }, [isLive]);

  return (
    <div className="glass-panel-lg flex flex-col overflow-hidden">
      {/* Toolbar */}
      <div className="flex items-center justify-between border-b border-scada-border px-4 py-2">
        <div className="flex items-center gap-3">
          <h2 className="text-xs font-bold uppercase tracking-wider text-scada-muted">
            Live Feed
          </h2>
          <span className="badge-blue">{frame.camera_id}</span>
          {isLive && (
            <span className="badge-red">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-scada-red" />
              LIVE
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[10px] text-scada-muted">
            {frame.resolution[0]}×{frame.resolution[1]}
          </span>
          <span className="text-[10px] text-scada-muted">
            {frame.processing_ms}ms
          </span>
          <button
            onClick={() => setIsLive(!isLive)}
            className={`rounded px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider transition ${
              isLive
                ? "bg-scada-red/20 text-scada-red hover:bg-scada-red/30"
                : "bg-scada-green/20 text-scada-green hover:bg-scada-green/30"
            }`}
          >
            {isLive ? "Pause" : "Resume"}
          </button>
        </div>
      </div>

      {/* Frame area */}
      <div className="relative aspect-[4/3] w-full bg-black/40 scan-overlay">
        {/* Rail track grid (simulated image) */}
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          className="absolute inset-0 h-full w-full"
        >
          {/* Dark gradient background */}
          <defs>
            <linearGradient id="bg-grad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#0f172a" />
              <stop offset="100%" stopColor="#1e293b" />
            </linearGradient>
            <radialGradient id="spot" cx="50%" cy="45%">
              <stop offset="0%" stopColor="#1e293b" stopOpacity="0.6" />
              <stop offset="100%" stopColor="#0f172a" stopOpacity="1" />
            </radialGradient>
          </defs>
          <rect width={WIDTH} height={HEIGHT} fill="url(#spot)" />

          {/* Gravel texture dots */}
          {Array.from({ length: 80 }).map((_, i) => (
            <circle
              key={i}
              cx={Math.random() * WIDTH}
              cy={Math.random() * HEIGHT}
              r={0.5 + Math.random() * 1.5}
              fill="#334155"
              opacity={0.3 + Math.random() * 0.3}
            />
          ))}
        </svg>

        {/* Detected lines overlay */}
        <OverlayCanvas lines={frame.lines} />

        {/* Crosshair */}
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <div className="h-6 w-px bg-scada-cyan/20" />
          <div className="absolute h-px w-6 bg-scada-cyan/20" />
          <div className="h-2 w-2 rounded-full border border-scada-cyan/30" />
        </div>

        {/* Corner brackets */}
        <svg className="absolute left-2 top-2 h-6 w-6 text-scada-cyan/40" viewBox="0 0 24 24">
          <path d="M0 8V0h8" fill="none" stroke="currentColor" strokeWidth="1.5" />
        </svg>
        <svg className="absolute right-2 top-2 h-6 w-6 text-scada-cyan/40" viewBox="0 0 24 24">
          <path d="M24 8V0h-8" fill="none" stroke="currentColor" strokeWidth="1.5" />
        </svg>
        <svg className="absolute bottom-2 left-2 h-6 w-6 text-scada-cyan/40" viewBox="0 0 24 24">
          <path d="M0 16v8h8" fill="none" stroke="currentColor" strokeWidth="1.5" />
        </svg>
        <svg className="absolute bottom-2 right-2 h-6 w-6 text-scada-cyan/40" viewBox="0 0 24 24">
          <path d="M24 16v8h-8" fill="none" stroke="currentColor" strokeWidth="1.5" />
        </svg>
      </div>

      {/* Footer bar */}
      <div className="flex items-center justify-between border-t border-scada-border px-4 py-2">
        <div className="flex items-center gap-4 text-[10px] text-scada-muted">
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
            <span className="font-bold text-scada-blue">
              {frame.lines.filter((l) => Math.abs(l.angle_deg) > 40).length}
            </span>
          </span>
        </div>
        <span className="text-[10px] text-scada-muted">
          {new Date(frame.timestamp).toLocaleTimeString("en-IN")}
        </span>
      </div>
    </div>
  );
}
