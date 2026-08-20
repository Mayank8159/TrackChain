// Leaflet/OSM map component rendering the track and defect markers.

"use client";

import React, { useState } from "react";
import type { DefectEvent } from "../../lib/types";

interface TrackMapProps {
  defects?: DefectEvent[];
  currentChainageM?: number;
  onSelectDefect?: (defect: DefectEvent) => void;
}

export function TrackMap({
  defects = [],
  currentChainageM = 12450,
  onSelectDefect,
}: TrackMapProps) {
  const [selectedDefect, setSelectedDefect] = useState<DefectEvent | null>(null);

  // Mock waypoints along a railway corridor (e.g. Delhi - Mumbai route sample)
  const waypoints = [
    { km: 0, label: "NDLS (New Delhi)", lat: 28.643, lng: 77.219 },
    { km: 5, label: "Hazrat Nizamuddin", lat: 28.588, lng: 77.253 },
    { km: 12, label: "Okhla Outer", lat: 28.535, lng: 77.284 },
    { km: 18, label: "Faridabad North", lat: 28.441, lng: 77.316 },
    { km: 25, label: "Ballabgarh", lat: 28.337, lng: 77.329 },
  ];

  return (
    <div className="relative w-full h-[450px] rounded-lg border border-scada-border bg-scada-bg overflow-hidden flex flex-col">
      {/* Map Header Overlay */}
      <div className="absolute top-3 left-3 z-10 flex items-center gap-3 bg-scada-panel/90 px-3 py-1.5 rounded border border-scada-border backdrop-blur">
        <span className="h-2 w-2 rounded-full bg-scada-green animate-pulse" />
        <span className="text-xs font-mono font-semibold text-scada-text">
          Track Section: NDLS-PWL Section (Km 0.000 to 25.000)
        </span>
        <span className="text-xs font-mono text-scada-cyan">
          GPS: 28.535° N, 77.284° E
        </span>
      </div>

      {/* SVG Canvas Map Graphic */}
      <div className="flex-1 w-full h-full relative scada-grid flex items-center justify-center p-8">
        <svg viewBox="0 0 800 350" className="w-full h-full">
          <defs>
            <linearGradient id="trackGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#00F0FF" stopOpacity="0.8" />
              <stop offset="100%" stopColor="#00E676" stopOpacity="0.8" />
            </linearGradient>
            <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          {/* Railway Polyline */}
          <path
            d="M 50,280 C 200,260 300,180 450,150 S 650,90 750,70"
            fill="none"
            stroke="#1E293B"
            strokeWidth="8"
            strokeLinecap="round"
          />
          <path
            d="M 50,280 C 200,260 300,180 450,150 S 650,90 750,70"
            fill="none"
            stroke="url(#trackGradient)"
            strokeWidth="3"
            strokeDasharray="6 4"
            filter="url(#glow)"
          />

          {/* Waypoints */}
          {waypoints.map((wp, idx) => {
            const x = 50 + idx * 175;
            const y = 280 - idx * 52;
            return (
              <g key={wp.label}>
                <circle cx={x} cy={y} r="5" fill="#111827" stroke="#00F0FF" strokeWidth="2" />
                <text x={x} y={y + 18} fill="#94A3B8" fontSize="10" fontFamily="monospace" textAnchor="middle">
                  {wp.label}
                </text>
                <text x={x} y={y + 28} fill="#00F0FF" fontSize="9" fontFamily="monospace" textAnchor="middle">
                  Km {wp.km}
                </text>
              </g>
            );
          })}

          {/* Inspection Vehicle Marker */}
          <g transform="translate(420, 155)">
            <circle cx="0" cy="0" r="12" fill="rgba(0, 240, 255, 0.2)" className="animate-ping" />
            <circle cx="0" cy="0" r="7" fill="#00F0FF" />
            <text x="0" y="-14" fill="#00F0FF" fontSize="10" fontFamily="monospace" textAnchor="middle" fontWeight="bold">
              Current Car (Km {(currentChainageM / 1000).toFixed(2)})
            </text>
          </g>

          {/* Defect Markers */}
          {defects.slice(0, 10).map((d, index) => {
            const ratio = Math.min(Math.max(d.chainageM / 25000, 0), 1);
            const x = 50 + ratio * 700;
            const y = 280 - ratio * 210 + ((index % 3) * 6 - 3);
            const isCrit = d.severity === "critical";

            return (
              <g
                key={d.id || index}
                className="cursor-pointer transition-transform hover:scale-125"
                onClick={() => {
                  setSelectedDefect(d);
                  onSelectDefect?.(d);
                }}
              >
                <circle
                  cx={x}
                  cy={y}
                  r="6"
                  fill={isCrit ? "#FF1744" : "#FFB300"}
                  stroke="#111827"
                  strokeWidth="1.5"
                />
                <circle
                  cx={x}
                  cy={y}
                  r="9"
                  fill="none"
                  stroke={isCrit ? "#FF1744" : "#FFB300"}
                  strokeWidth="1"
                  opacity="0.6"
                />
              </g>
            );
          })}
        </svg>
      </div>

      {/* Selected Defect Floating Card */}
      {selectedDefect && (
        <div className="absolute bottom-3 right-3 z-10 bg-scada-panel/95 p-3 rounded-lg border border-scada-border-bright text-xs font-mono shadow-xl max-w-xs">
          <div className="flex items-center justify-between gap-2 border-b border-scada-border pb-1 mb-2">
            <span className="font-bold text-scada-red uppercase">{selectedDefect.defectClass}</span>
            <button
              onClick={() => setSelectedDefect(null)}
              className="text-scada-muted hover:text-scada-text"
            >
              ✕
            </button>
          </div>
          <p className="text-scada-muted">Chainage: <span className="text-scada-text">{(selectedDefect.chainageM / 1000).toFixed(3)} km</span></p>
          <p className="text-scada-muted">Severity: <span className="text-scada-amber uppercase">{selectedDefect.severity}</span></p>
          <p className="text-scada-muted">Source: <span className="text-scada-cyan">{selectedDefect.streamSource} stream</span></p>
        </div>
      )}
    </div>
  );
}
