"use client";

import React, { useState, useEffect, useMemo, useRef } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import {
  Box,
  Eye,
  Camera,
  Layers,
  Play,
  Pause,
  RotateCcw,
  Sliders,
  ShieldAlert,
  Sparkles,
  Zap,
  Activity,
  Maximize2,
  Compass,
  ArrowRight,
} from "lucide-react";
import { useTelemetry } from "@/hooks/useTelemetry";
import { useDefects } from "@/hooks/useDefects";
import { usePlaybackSync } from "@/hooks/usePlaybackSync";
import { MOCK_TELEMETRY_SERIES, MOCK_DEFECTS } from "@/lib/mock-provider";
import { projectTelemetryTo3D, type Projected3DTrack } from "@/lib/track-3d-math";
import type { CameraMode } from "@/components/digital-twin/CameraController";
import type { TrackLayers } from "@/components/digital-twin/TrackCorridor";
import type { DefectEvent, TelemetryPoint } from "@/lib/types";
import { formatChainage, formatConfidence } from "@/lib/format";
import { getSeverityMeta } from "@/lib/severity";
import { TelemetryChart } from "@/components/charts/TelemetryChart";
import { VideoPlayer } from "@/components/video/VideoPlayer";
import { TrackMap } from "@/components/map/TrackMap";

// Dynamically import Scene3D with SSR disabled for WebGL canvas
const Scene3D = dynamic(
  () =>
    import("@/components/digital-twin/Scene3D").then((mod) => mod.Scene3D),
  { ssr: false }
);

export default function DigitalTwinPage() {
  const { data: rawTelemetry = MOCK_TELEMETRY_SERIES } = useTelemetry("ses-delhi-agra-001");
  const { defects = MOCK_DEFECTS } = useDefects();

  // 3D & Playback Controls State
  const [cameraMode, setCameraMode] = useState<CameraMode>("follow");
  const [is2DFallback, setIs2DFallback] = useState(false);
  const [isAutoFlyThrough, setIsAutoFlyThrough] = useState(true);
  const [flySpeedKmh, setFlySpeedKmh] = useState(130);
  const [selectedDefectId, setSelectedDefectId] = useState<string | undefined>(
    defects[0]?.id
  );
  const [selectedMetric, setSelectedMetric] = useState<
    "trackGaugeMm" | "cantMm" | "twistMmPerM" | "vibrationRms"
  >("trackGaugeMm");

  const [layers, setLayers] = useState<TrackLayers>({
    rails: true,
    sleepers: true,
    heatmap: true,
    centerLine: false,
    ballast: true,
  });

  const [showLayerMenu, setShowLayerMenu] = useState(false);

  // Math projection: Convert 1D Telemetry to 3D Cartesian vertex buffers & instanced matrices
  const projectedTrack = useMemo(() => {
    return projectTelemetryTo3D(rawTelemetry);
  }, [rawTelemetry]);

  // Bi-directional Playback Sync
  const videoRef = useRef<any>(null);
  const {
    currentTime,
    currentChainageM,
    seekToChainage,
    handleVideoTimeUpdate,
  } = usePlaybackSync({
    telemetryData: rawTelemetry,
    videoDurationSec: 60,
    videoRef,
  });

  // Auto Fly-Through Animation Timer (when Follow Mode or Fly-Through is active)
  useEffect(() => {
    if (!isAutoFlyThrough) return;

    const minZ = projectedTrack.minZ || 0;
    const maxZ = projectedTrack.maxZ || 15000;
    const speedMps = (flySpeedKmh * 1000) / 3600; // e.g. 130 km/h = 36.1 m/s

    const intervalMs = 50;
    const deltaMeters = (speedMps * intervalMs) / 1000;

    const timer = setInterval(() => {
      const nextChainage = currentChainageM + deltaMeters;
      if (nextChainage > maxZ) {
        seekToChainage(minZ);
      } else {
        seekToChainage(nextChainage);
      }
    }, intervalMs);

    return () => clearInterval(timer);
  }, [isAutoFlyThrough, flySpeedKmh, currentChainageM, projectedTrack, seekToChainage]);

  // Find nearest telemetry point to current chainage for HUD
  const currentTelemetry = useMemo(() => {
    if (!rawTelemetry || rawTelemetry.length === 0) return null;
    let closest = rawTelemetry[0];
    let minDiff = Infinity;
    for (const pt of rawTelemetry) {
      const diff = Math.abs(pt.chainageM - currentChainageM);
      if (diff < minDiff) {
        minDiff = diff;
        closest = pt;
      }
    }
    return closest;
  }, [rawTelemetry, currentChainageM]);

  // Selected Defect Object
  const selectedDefect = useMemo(() => {
    return defects.find((d) => d.id === selectedDefectId) || defects[0];
  }, [defects, selectedDefectId]);

  const handleSelectDefect = (defect: DefectEvent) => {
    setSelectedDefectId(defect.id);
    seekToChainage(defect.chainageM);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)] bg-[#020617] text-slate-200 overflow-hidden font-sans select-none">
      {/* ========================================================================= */}
      {/* 1. Header Controls Ribbon                                                 */}
      {/* ========================================================================= */}
      <header className="flex-shrink-0 flex flex-wrap items-center justify-between gap-3 px-4 py-2 border-b border-white/[0.08] bg-slate-950/90 backdrop-blur-2xl z-30">
        {/* Left: Title & Section */}
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-control bg-cyan-500/15 border border-cyan-500/40 text-cyan-400 shadow-[0_0_12px_rgba(6,182,212,0.3)]">
            <Box size={18} strokeWidth={1.8} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xs font-mono font-bold tracking-wider text-slate-100 uppercase">
                3D Digital Twin: KM 0.000 – 25.000
              </h1>
              <span className="badge-cyan text-[9px] font-mono font-bold px-1.5 py-0.2">
                R3F WEBGL
              </span>
            </div>
            <p className="text-[10px] font-mono text-slate-400">
              NDLS–AGC Mainline • Broad Gauge 1676mm • 60 FPS Procedural Mesh
            </p>
          </div>
        </div>

        {/* Center: Camera Modes & Fly-Through Playback */}
        <div className="flex items-center gap-2">
          {/* Camera Mode Switcher */}
          <div className="flex items-center rounded-control bg-slate-900 border border-white/10 p-0.5">
            <button
              onClick={() => setCameraMode("follow")}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] font-mono transition-all ${
                cameraMode === "follow"
                  ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-bold shadow-[0_0_8px_rgba(6,182,212,0.25)]"
                  : "text-slate-400 hover:text-slate-200"
              }`}
              title="Follow Camera (Behind Train)"
            >
              <Camera size={13} />
              <span>FOLLOW</span>
            </button>
            <button
              onClick={() => setCameraMode("orbit")}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] font-mono transition-all ${
                cameraMode === "orbit"
                  ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-bold shadow-[0_0_8px_rgba(6,182,212,0.25)]"
                  : "text-slate-400 hover:text-slate-200"
              }`}
              title="Free Orbit Camera (360° Rotate)"
            >
              <Compass size={13} />
              <span>ORBIT</span>
            </button>
            <button
              onClick={() => setCameraMode("topdown")}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] font-mono transition-all ${
                cameraMode === "topdown"
                  ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-bold shadow-[0_0_8px_rgba(6,182,212,0.25)]"
                  : "text-slate-400 hover:text-slate-200"
              }`}
              title="Top Down Plan View"
            >
              <Eye size={13} />
              <span>TOP-DOWN</span>
            </button>
          </div>

          {/* Auto Fly-Through Play/Pause */}
          <button
            onClick={() => setIsAutoFlyThrough(!isAutoFlyThrough)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-control text-[11px] font-mono border transition-all ${
              isAutoFlyThrough
                ? "bg-emerald-500/15 border-emerald-500/40 text-emerald-300 shadow-[0_0_10px_rgba(16,185,129,0.25)]"
                : "bg-slate-900 border-white/10 text-slate-300 hover:bg-slate-800"
            }`}
            title={isAutoFlyThrough ? "Pause Fly-Through" : "Start 3D Fly-Through"}
          >
            {isAutoFlyThrough ? (
              <>
                <Pause size={13} className="text-emerald-400" />
                <span className="font-bold">FLYING</span>
              </>
            ) : (
              <>
                <Play size={13} className="text-slate-400 fill-current ml-0.5" />
                <span>FLY-THRU</span>
              </>
            )}
          </button>
        </div>

        {/* Right: Layers & 2D Fallback Accessibility Toggle */}
        <div className="flex items-center gap-2">
          {/* Layer Visibility Menu */}
          <div className="relative">
            <button
              onClick={() => setShowLayerMenu(!showLayerMenu)}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-control text-[11px] font-mono border transition-all ${
                showLayerMenu
                  ? "bg-cyan-500/15 border-cyan-500/40 text-cyan-300"
                  : "bg-slate-900 border-white/10 text-slate-300 hover:bg-slate-800"
              }`}
            >
              <Layers size={13} />
              <span>LAYERS</span>
            </button>

            {showLayerMenu && (
              <div className="absolute right-0 top-full mt-2 w-48 rounded-control border border-white/10 bg-slate-950/95 p-2 shadow-2xl backdrop-blur-xl z-50 flex flex-col gap-1.5">
                <span className="text-[9px] font-mono uppercase tracking-widest text-slate-500 px-2 py-1">
                  Visible Meshes
                </span>
                <label className="flex items-center justify-between px-2 py-1 text-xs font-mono rounded hover:bg-white/5 cursor-pointer">
                  <span>Rails</span>
                  <input
                    type="checkbox"
                    checked={layers.rails}
                    onChange={(e) =>
                      setLayers({ ...layers, rails: e.target.checked })
                    }
                    className="accent-cyan-400"
                  />
                </label>
                <label className="flex items-center justify-between px-2 py-1 text-xs font-mono rounded hover:bg-white/5 cursor-pointer">
                  <span>Instanced Sleepers</span>
                  <input
                    type="checkbox"
                    checked={layers.sleepers}
                    onChange={(e) =>
                      setLayers({ ...layers, sleepers: e.target.checked })
                    }
                    className="accent-cyan-400"
                  />
                </label>
                <label className="flex items-center justify-between px-2 py-1 text-xs font-mono rounded hover:bg-white/5 cursor-pointer">
                  <span>TQI Heatmap</span>
                  <input
                    type="checkbox"
                    checked={layers.heatmap}
                    onChange={(e) =>
                      setLayers({ ...layers, heatmap: e.target.checked })
                    }
                    className="accent-cyan-400"
                  />
                </label>
                <label className="flex items-center justify-between px-2 py-1 text-xs font-mono rounded hover:bg-white/5 cursor-pointer">
                  <span>Ballast Bed</span>
                  <input
                    type="checkbox"
                    checked={layers.ballast}
                    onChange={(e) =>
                      setLayers({ ...layers, ballast: e.target.checked })
                    }
                    className="accent-cyan-400"
                  />
                </label>
              </div>
            )}
          </div>

          {/* 2D Accessibility Fallback Switch */}
          <button
            onClick={() => setIs2DFallback(!is2DFallback)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-control text-[11px] font-mono font-bold transition-all border ${
              is2DFallback
                ? "bg-amber-500/15 border-amber-500/40 text-amber-300 shadow-[0_0_10px_rgba(245,158,11,0.25)]"
                : "bg-slate-900 border-white/10 text-slate-400 hover:text-slate-200"
            }`}
            title="Toggle 2D Map fallback for older hardware or vestibular accessibility"
          >
            <span>{is2DFallback ? "2D FALLBACK ACTIVE" : "2D FALLBACK"}</span>
          </button>
        </div>
      </header>

      {/* ========================================================================= */}
      {/* 2. Main 3-Pane Body Grid                                                  */}
      {/* ========================================================================= */}
      <main className="flex-1 grid grid-cols-1 lg:grid-cols-12 overflow-hidden">
        {/* Left / Center Viewport (7 Cols = ~60% Width) */}
        <section className="lg:col-span-7 h-full flex flex-col relative border-r border-white/[0.08] bg-[#020617] overflow-hidden">
          {!is2DFallback ? (
            <>
              {/* 3D WebGL Scene */}
              <div className="flex-1 w-full h-full relative">
                <Scene3D
                  projectedTrack={projectedTrack}
                  defects={defects}
                  selectedDefectId={selectedDefectId}
                  onSelectDefect={handleSelectDefect}
                  onSeekChainage={seekToChainage}
                  currentChainageM={currentChainageM}
                  cameraMode={cameraMode}
                  layers={layers}
                />

                {/* Floating SCADA Telemetry HUD Overlay */}
                <div className="absolute top-4 left-4 z-10 flex flex-col gap-2 pointer-events-none">
                  {/* Real-time Chainage & Kinematics Card */}
                  <div className="flex items-center gap-3 p-3 rounded-control border border-white/10 bg-slate-950/80 backdrop-blur-md shadow-2xl font-mono">
                    <div className="flex flex-col">
                      <span className="text-[9px] uppercase tracking-wider text-slate-500">
                        Current Chainage
                      </span>
                      <span className="text-base font-bold text-cyan-300">
                        {formatChainage(currentChainageM)}
                      </span>
                    </div>
                    <div className="h-6 w-px bg-white/10" />
                    <div className="flex flex-col">
                      <span className="text-[9px] uppercase tracking-wider text-slate-500">
                        Speed
                      </span>
                      <span className="text-base font-bold text-emerald-400">
                        {Math.round(currentTelemetry?.speedKmh || flySpeedKmh)}{" "}
                        <span className="text-[10px] font-normal text-slate-400">km/h</span>
                      </span>
                    </div>
                    <div className="h-6 w-px bg-white/10" />
                    <div className="flex flex-col">
                      <span className="text-[9px] uppercase tracking-wider text-slate-500">
                        Track Gauge
                      </span>
                      <span className="text-sm font-bold text-slate-200">
                        {(currentTelemetry?.trackGaugeMm || 1676).toFixed(1)}{" "}
                        <span className="text-[9px] text-slate-400">mm</span>
                      </span>
                    </div>
                  </div>

                  {/* GPU Instancing & FPS Indicator */}
                  <div className="flex items-center gap-2 px-2.5 py-1 rounded-control bg-slate-950/70 border border-white/5 backdrop-blur font-mono text-[10px] text-slate-400 w-fit">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    <span>60 FPS • {projectedTrack.sleeperMatrices.length} Instanced Sleepers</span>
                  </div>
                </div>

                {/* Bottom Quick Jump Ribbon to 3D Defects */}
                <div className="absolute bottom-4 left-4 right-4 z-10 flex items-center justify-between gap-2 p-2 rounded-control border border-white/10 bg-slate-950/85 backdrop-blur-md">
                  <div className="flex items-center gap-2 overflow-x-auto py-0.5">
                    <span className="text-[10px] font-mono text-slate-500 uppercase shrink-0 pl-1">
                      Jump To 3D Defect:
                    </span>
                    {defects.slice(0, 5).map((d) => {
                      const isSel = d.id === selectedDefectId;
                      const meta = getSeverityMeta(d.severity);
                      return (
                        <button
                          key={d.id}
                          onClick={() => handleSelectDefect(d)}
                          className={`flex items-center gap-1.5 px-2 py-1 rounded text-[10px] font-mono shrink-0 transition-all border ${
                            isSel
                              ? "bg-cyan-500/20 border-cyan-400 text-cyan-200 font-bold"
                              : "bg-slate-900/60 border-white/5 text-slate-400 hover:text-white"
                          }`}
                        >
                          <span
                            className="h-2 w-2 rounded-full shrink-0"
                            style={{ backgroundColor: meta.hex }}
                          />
                          <span>{d.id}</span>
                          <span className="text-slate-500">
                            ({(d.chainageM / 1000).toFixed(1)}k)
                          </span>
                        </button>
                      );
                    })}
                  </div>
                  <button
                    onClick={() => seekToChainage(projectedTrack.minZ)}
                    className="p-1 text-slate-400 hover:text-white rounded hover:bg-white/5 transition-colors"
                    title="Reset to start"
                  >
                    <RotateCcw size={14} />
                  </button>
                </div>
              </div>
            </>
          ) : (
            /* 2D Fallback GIS Corridor View */
            <div className="flex-1 flex flex-col p-4 gap-4 overflow-y-auto">
              <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-control flex items-center gap-3">
                <ShieldAlert size={20} className="text-amber-400 shrink-0" />
                <div className="text-xs font-mono text-amber-200">
                  <strong>2D ACCESSIBILITY / LOW-POWER MODE</strong>
                  <p className="text-[11px] text-amber-300/80">
                    WebGL canvas unmounted. All spatial and temporal playhead sync remains active.
                  </p>
                </div>
              </div>
              <TrackMap
                defects={defects}
                currentChainageM={currentChainageM}
                selectedDefectId={selectedDefectId}
                onSelectDefect={handleSelectDefect}
                className="flex-1 min-h-[420px]"
              />
            </div>
          )}
        </section>

        {/* Right Stack (5 Cols = ~40% Width, Split 50/50 Vertically) */}
        <section className="lg:col-span-5 h-full flex flex-col bg-[#030914] overflow-hidden">
          {/* Top Half: Synchronized 2D Telemetry Waveforms */}
          <div className="h-1/2 flex flex-col border-b border-white/[0.08] p-3 overflow-hidden">
            {/* Telemetry Header with Metric Tabs */}
            <div className="flex items-center justify-between pb-2 mb-1 border-b border-white/5">
              <div className="flex items-center gap-2">
                <Activity size={14} className="text-cyan-400" />
                <span className="font-mono text-[11px] font-bold text-slate-200 uppercase">
                  Telemetry Sync Waveform
                </span>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setSelectedMetric("trackGaugeMm")}
                  className={`px-1.5 py-0.5 rounded text-[9px] font-mono transition-all ${
                    selectedMetric === "trackGaugeMm"
                      ? "bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/30"
                      : "text-slate-500 hover:text-slate-300"
                  }`}
                >
                  GAUGE
                </button>
                <button
                  onClick={() => setSelectedMetric("cantMm")}
                  className={`px-1.5 py-0.5 rounded text-[9px] font-mono transition-all ${
                    selectedMetric === "cantMm"
                      ? "bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/30"
                      : "text-slate-500 hover:text-slate-300"
                  }`}
                >
                  CANT
                </button>
                <button
                  onClick={() => setSelectedMetric("twistMmPerM")}
                  className={`px-1.5 py-0.5 rounded text-[9px] font-mono transition-all ${
                    selectedMetric === "twistMmPerM"
                      ? "bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/30"
                      : "text-slate-500 hover:text-slate-300"
                  }`}
                >
                  TWIST
                </button>
                <button
                  onClick={() => setSelectedMetric("vibrationRms")}
                  className={`px-1.5 py-0.5 rounded text-[9px] font-mono transition-all ${
                    selectedMetric === "vibrationRms"
                      ? "bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/30"
                      : "text-slate-500 hover:text-slate-300"
                  }`}
                >
                  VIB
                </button>
              </div>
            </div>

            {/* Recharts Waveform with Live Playhead */}
            <div className="flex-1 min-h-0">
              <TelemetryChart
                data={rawTelemetry}
                metricKey={selectedMetric}
                currentChainageM={currentChainageM}
                defects={defects}
                onSeekChainage={seekToChainage}
                height={160}
              />
            </div>
          </div>

          {/* Bottom Half: Synchronized Optical Video Evidence */}
          <div className="h-1/2 flex flex-col p-3 bg-slate-950/60 overflow-hidden relative">
            <div className="flex items-center justify-between pb-2 mb-1 border-b border-white/5">
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-red-500 animate-pulse" />
                <span className="font-mono text-[11px] font-bold text-slate-200 uppercase">
                  Optical Evidence Sync (Bogie Vision)
                </span>
              </div>
              <span className="text-[10px] font-mono text-cyan-400">
                t = {currentTime.toFixed(1)}s
              </span>
            </div>

            {/* Video Player Component with Bounding Boxes */}
            <div className="flex-1 min-h-0 relative rounded border border-white/10 overflow-hidden">
              <VideoPlayer
                ref={videoRef}
                src=""
                initialTime={currentTime}
                onTimeUpdate={handleVideoTimeUpdate}
                defects={defects}
                className="h-full w-full rounded-none border-none"
              />
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
