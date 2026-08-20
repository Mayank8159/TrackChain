// Video playback synced with telemetry graphs; seeks to defect timestamps.

"use client";

import React, { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { Header } from "@/components/Header";
import { Card } from "@/components/ui/Card";
import { TelemetryChart } from "@/components/charts/TelemetryChart";
import { StatBadge } from "@/components/ui/StatBadge";
import type { TelemetryPoint } from "@/lib/types";

// Generate synthetic telemetry points synced along a 60-second inspection video clip
function generateSyncedTelemetry(): TelemetryPoint[] {
  const points: TelemetryPoint[] = [];
  for (let i = 0; i <= 60; i++) {
    const chainage = 12000 + i * 20; // 20 meters per second (~72 km/h)
    const hasAnomaly = i >= 25 && i <= 30;

    points.push({
      id: `tel-${i}`,
      sessionId: "SES-20260821-01",
      timestamp: new Date(Date.now() - (60 - i) * 1000).toISOString(),
      chainageM: chainage,
      speedKmh: 72 + (Math.sin(i / 5) * 2),
      vibrationRms: hasAnomaly ? 2.8 + Math.random() * 0.8 : 0.8 + Math.random() * 0.3,
      trackGaugeMm: hasAnomaly ? 1446 + Math.random() * 3 : 1435 + (Math.random() * 2 - 1),
      cantMm: 12 + Math.sin(i / 10) * 5,
      twistMmPerM: hasAnomaly ? 3.8 + Math.random() * 0.5 : 1.2 + Math.random() * 0.4,
      verticalUnevennessMm: hasAnomaly ? 5.2 : 1.1,
      alignmentDevMm: hasAnomaly ? 7.4 : 1.8,
    });
  }
  return points;
}

export default function VideoPlaybackPage() {
  const searchParams = useSearchParams();
  const seekParam = searchParams.get("seek");

  const [telemetryData] = useState<TelemetryPoint[]>(generateSyncedTelemetry);
  const [currentSec, setCurrentSec] = useState<number>(
    seekParam ? Math.min(Number(seekParam) % 60, 60) : 0
  );
  const [isPlaying, setIsPlaying] = useState<boolean>(true);
  const [selectedMetric, setSelectedMetric] = useState<
    "vibrationRms" | "speedKmh" | "trackGaugeMm" | "cantMm" | "twistMmPerM"
  >("vibrationRms");

  useEffect(() => {
    if (!isPlaying) return;
    const timer = setInterval(() => {
      setCurrentSec((prev) => (prev >= 60 ? 0 : prev + 1));
    }, 1000);
    return () => clearInterval(timer);
  }, [isPlaying]);

  const currentPoint =
    telemetryData[Math.floor(currentSec)] || telemetryData[0];

  return (
    <div className="min-h-screen flex flex-col bg-scada-bg text-scada-text font-sans">
      <Header />
      <div className="glow-line" />

      <main className="flex-1 p-4 lg:p-6 flex flex-col gap-6 max-w-7xl mx-auto w-full">
        {/* Title */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold font-mono tracking-wider text-scada-text uppercase">
              Synchronized Video & Telemetry Playback
            </h1>
            <p className="text-xs font-mono text-scada-muted">
              Correlated optical video and high-frequency IMU sensor feeds
            </p>
          </div>

          <div className="flex items-center gap-3">
            <StatBadge severity={currentPoint?.vibrationRms > 2.0 ? "critical" : "normal"}>
              {currentPoint?.vibrationRms > 2.0 ? "FAULT ZONE" : "NOMINAL TRACK"}
            </StatBadge>
            <span className="text-xs font-mono text-scada-cyan">
              Time: {currentSec.toString().padStart(2, "0")}:00 / 01:00
            </span>
          </div>
        </div>

        {/* Video & Telemetry Stack */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Video Player (2 cols) */}
          <div className="lg:col-span-2 flex flex-col gap-4">
            <div className="relative aspect-video w-full rounded-lg border border-scada-border bg-black/60 overflow-hidden flex flex-col justify-between p-4 scada-grid">
              {/* Top Overlay */}
              <div className="flex items-center justify-between z-10">
                <div className="flex items-center gap-2">
                  <span className="badge-red">
                    <span className="h-1.5 w-1.5 rounded-full bg-scada-red animate-pulse" />
                    CAM-LEFT-RAIL
                  </span>
                  <span className="badge-cyan">HD 1080p60</span>
                </div>
                <span className="text-xs font-mono text-scada-muted bg-scada-panel/80 px-2 py-0.5 rounded border border-scada-border">
                  Chainage: {(currentPoint?.chainageM / 1000).toFixed(3)} km
                </span>
              </div>

              {/* Simulated Rail Inspection Graphic */}
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <svg viewBox="0 0 600 340" className="w-full h-full opacity-70">
                  {/* Rails */}
                  <line x1="150" y1="340" x2="250" y2="120" stroke="#00F0FF" strokeWidth="4" />
                  <line x1="450" y1="340" x2="350" y2="120" stroke="#00F0FF" strokeWidth="4" />
                  {/* Sleepers */}
                  {[0.2, 0.4, 0.6, 0.8].map((ratio, i) => {
                    const y = 120 + ratio * 220;
                    const x1 = 250 - ratio * 100;
                    const x2 = 350 + ratio * 100;
                    return (
                      <line
                        key={i}
                        x1={x1}
                        y1={y}
                        x2={x2}
                        y2={y}
                        stroke="#334155"
                        strokeWidth="8"
                      />
                    );
                  })}
                  {/* Anomaly box if in fault zone */}
                  {currentSec >= 25 && currentSec <= 30 && (
                    <g transform="translate(190, 220)">
                      <rect
                        width="70"
                        height="40"
                        fill="rgba(255, 23, 68, 0.2)"
                        stroke="#FF1744"
                        strokeWidth="2"
                        strokeDasharray="4 2"
                      />
                      <text x="5" y="-6" fill="#FF1744" fontSize="11" fontFamily="monospace" fontWeight="bold">
                        CRACK DETECTED
                      </text>
                    </g>
                  )}
                </svg>
              </div>

              {/* Player Controls Bar */}
              <div className="z-10 flex flex-col gap-2 bg-scada-panel/90 p-3 rounded-lg border border-scada-border backdrop-blur">
                {/* Timeline scrubber */}
                <input
                  type="range"
                  min="0"
                  max="60"
                  value={currentSec}
                  onChange={(e) => setCurrentSec(Number(e.target.value))}
                  className="w-full h-1 bg-scada-border rounded-lg appearance-none cursor-pointer accent-scada-cyan"
                />

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => setIsPlaying(!isPlaying)}
                      className="px-3 py-1 rounded bg-scada-cyan/20 border border-scada-cyan text-scada-cyan text-xs font-mono font-bold uppercase hover:bg-scada-cyan/30"
                    >
                      {isPlaying ? "Pause" : "Play"}
                    </button>
                    <button
                      onClick={() => setCurrentSec(26)}
                      className="px-2 py-1 rounded bg-scada-red/20 border border-scada-red text-scada-red text-xs font-mono hover:bg-scada-red/30"
                    >
                      Jump to Defect (00:26)
                    </button>
                  </div>
                  <span className="text-xs font-mono text-scada-muted">
                    Speed: {currentPoint?.speedKmh.toFixed(1)} km/h
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Real-time Telemetry Metrics (1 col) */}
          <div className="flex flex-col gap-4">
            <Card title="Instantaneous Telemetry">
              <div className="flex flex-col gap-3 font-mono text-xs">
                <div className="flex justify-between border-b border-scada-border pb-1.5">
                  <span className="text-scada-muted">Chainage:</span>
                  <span className="text-scada-cyan font-bold">
                    {(currentPoint?.chainageM / 1000).toFixed(3)} km
                  </span>
                </div>
                <div className="flex justify-between border-b border-scada-border pb-1.5">
                  <span className="text-scada-muted">Track Gauge:</span>
                  <span
                    className={
                      currentPoint?.trackGaugeMm > 1445
                        ? "text-scada-red font-bold"
                        : "text-scada-green"
                    }
                  >
                    {currentPoint?.trackGaugeMm.toFixed(1)} mm
                  </span>
                </div>
                <div className="flex justify-between border-b border-scada-border pb-1.5">
                  <span className="text-scada-muted">Vibration RMS:</span>
                  <span
                    className={
                      currentPoint?.vibrationRms > 2.0
                        ? "text-scada-red font-bold"
                        : "text-scada-cyan"
                    }
                  >
                    {currentPoint?.vibrationRms.toFixed(2)} g
                  </span>
                </div>
                <div className="flex justify-between border-b border-scada-border pb-1.5">
                  <span className="text-scada-muted">Cant (Superelevation):</span>
                  <span className="text-scada-text">
                    {currentPoint?.cantMm.toFixed(1)} mm
                  </span>
                </div>
                <div className="flex justify-between border-b border-scada-border pb-1.5">
                  <span className="text-scada-muted">Track Twist:</span>
                  <span
                    className={
                      currentPoint?.twistMmPerM > 3.0
                        ? "text-scada-amber font-bold"
                        : "text-scada-text"
                    }
                  >
                    {currentPoint?.twistMmPerM.toFixed(2)} mm/m
                  </span>
                </div>
              </div>
            </Card>

            <Card title="Select Graph Metric">
              <div className="flex flex-wrap gap-2">
                {[
                  { key: "vibrationRms", label: "Vibration RMS" },
                  { key: "speedKmh", label: "Speed" },
                  { key: "trackGaugeMm", label: "Track Gauge" },
                  { key: "cantMm", label: "Cant" },
                  { key: "twistMmPerM", label: "Twist" },
                ].map((m) => (
                  <button
                    key={m.key}
                    onClick={() => setSelectedMetric(m.key as any)}
                    className={`px-2.5 py-1 rounded text-xs font-mono uppercase transition ${
                      selectedMetric === m.key
                        ? "bg-scada-cyan/20 text-scada-cyan border border-scada-cyan"
                        : "bg-scada-panel text-scada-muted border border-scada-border hover:text-scada-text"
                    }`}
                  >
                    {m.label}
                  </button>
                ))}
              </div>
            </Card>
          </div>
        </div>

        {/* Telemetry Chart below video */}
        <Card title={`Synced Telemetry Profile: ${selectedMetric.toUpperCase()}`}>
          <TelemetryChart
            data={telemetryData}
            metricKey={selectedMetric}
            height={160}
          />
        </Card>
      </main>
    </div>
  );
}
