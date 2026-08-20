// Chainage/time scrubber; jumps playback to defect timestamps.

"use client";

import React from "react";
import type { DefectEvent } from "../../lib/types";
import { formatDuration } from "../../lib/format";

interface VideoTimelineProps {
  durationSec: number;
  currentSec: number;
  defects?: DefectEvent[];
  onSeek: (timeSec: number) => void;
}

export function VideoTimeline({
  durationSec = 60,
  currentSec,
  defects = [],
  onSeek,
}: VideoTimelineProps) {
  return (
    <div className="flex flex-col gap-2 font-mono text-xs">
      <div className="flex items-center justify-between text-scada-muted text-[10px]">
        <span>{formatDuration(currentSec)}</span>
        <span>Inspection Run Timeline</span>
        <span>{formatDuration(durationSec)}</span>
      </div>

      <div className="relative flex items-center h-6 w-full">
        {/* Scrubber slider */}
        <input
          type="range"
          min={0}
          max={durationSec}
          step={0.5}
          value={currentSec}
          onChange={(e) => onSeek(Number(e.target.value))}
          className="w-full h-1.5 bg-scada-panel-header rounded-lg appearance-none cursor-pointer accent-scada-cyan border border-scada-border z-10"
        />

        {/* Defect Markers on Timeline */}
        {defects.map((d, i) => {
          if (d.videoTimestampSec === undefined) return null;
          const leftPct = (d.videoTimestampSec / durationSec) * 100;
          const isCrit = d.severity === "critical";

          return (
            <button
              key={d.id || i}
              onClick={() => onSeek(d.videoTimestampSec!)}
              style={{ left: `${leftPct}%` }}
              className={`absolute top-1/2 -translate-y-1/2 -translate-x-1/2 h-3.5 w-3.5 rounded-full border-2 border-scada-bg z-20 transition-transform hover:scale-150 ${
                isCrit ? "bg-scada-red animate-pulse" : "bg-scada-amber"
              }`}
              title={`${d.defectClass} at ${formatDuration(d.videoTimestampSec)}`}
            />
          );
        })}
      </div>
    </div>
  );
}
