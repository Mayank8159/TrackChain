// Deep Telemetry, Model Status, Detection Summary, and Execution Terminal (tc.v1).

"use client";

import React from "react";
import {
  Cpu,
  Zap,
  Activity,
  Layers,
  Terminal,
  ShieldCheck,
  AlertTriangle,
  FileCode,
  Image as ImageIcon,
  CheckCircle2,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import type { InferenceResult, ImageProvenance } from "@/lib/types";

interface TelemetrySidebarProps {
  result: InferenceResult | null;
  fps: number;
  logs: string[];
  provenanceList: ImageProvenance[];
  selectedSampleId: string | null;
  onSelectSample: (sample: ImageProvenance) => void;
}

export function TelemetrySidebar({
  result,
  fps,
  logs,
  provenanceList,
  selectedSampleId,
  onSelectSample,
}: TelemetrySidebarProps) {
  const yoloLoaded = result?.yolo_weights_loaded ?? false;
  const railsCount = result?.rails?.length || 0;
  const sleepersCount = result?.sleepers?.length || 0;
  const boxesCount = result?.yolo_boxes?.length || 0;

  return (
    <div className="flex flex-col gap-5 w-full font-mono text-xs">
      {/* 1. Model Perception Status */}
      <Card
        title="Edge Perception Models"
        badge={
          <span className="badge-cyan text-[10px] flex items-center gap-1">
            <Cpu size={10} />
            STACK v2.4
          </span>
        }
      >
        <div className="space-y-2.5 p-1">
          <div className="flex items-center justify-between border-b border-scada-border/60 pb-2">
            <span className="text-scada-muted">Hough Geometry Engine:</span>
            <span className="badge-green text-[10px]">ACTIVE (OpenCV)</span>
          </div>

          <div className="flex items-center justify-between border-b border-scada-border/60 pb-2">
            <span className="text-scada-muted">YOLOv8-Rail Detector:</span>
            {yoloLoaded ? (
              <span className="badge-green text-[10px]">WEIGHTS ACTIVE</span>
            ) : (
              <span className="badge-amber text-[10px]">WEIGHTS MISSING</span>
            )}
          </div>

          <div className="flex items-center justify-between">
            <span className="text-scada-muted">Target Architecture:</span>
            <span className="text-white font-bold">ARM64 NEON / TensorRT</span>
          </div>
        </div>
      </Card>

      {/* 2. Real-Time Latency & Perceptual Telemetry */}
      <div className="grid grid-cols-2 gap-3">
        <div className="scada-card p-3 border border-scada-border space-y-1">
          <span className="text-[10px] text-scada-muted uppercase font-bold">
            Inference Delta
          </span>
          <p className="text-xl font-bold text-cyan-400">
            {result ? `${result.inference_ms.toFixed(1)} ms` : "--"}
          </p>
          <p className="text-[9px] text-scada-muted">Target: &lt; 50ms</p>
        </div>

        <div className="scada-card p-3 border border-scada-border space-y-1">
          <span className="text-[10px] text-scada-muted uppercase font-bold">
            Optical Stream FPS
          </span>
          <p className="text-xl font-bold text-emerald-400">
            {fps > 0 ? `${fps.toFixed(1)} FPS` : "2.0 FPS"}
          </p>
          <p className="text-[9px] text-scada-muted">Throttled Ingest</p>
        </div>
      </div>

      {/* 3. Detection Breakdown */}
      <Card title="Frame Detection Breakdown">
        <div className="space-y-2 p-1 text-[11px]">
          <div className="flex items-center justify-between border-b border-scada-border/60 pb-1.5">
            <span className="text-scada-muted">• Running Rails:</span>
            <span className="font-bold text-cyan-300">{railsCount} detected</span>
          </div>

          <div className="flex items-center justify-between border-b border-scada-border/60 pb-1.5">
            <span className="text-scada-muted">• Sleepers (Ties):</span>
            <span className="font-bold text-emerald-300">{sleepersCount} segmented</span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-scada-muted">• Fastener Faults:</span>
            <span className="font-bold text-amber-300">
              {yoloLoaded ? `${boxesCount} flagged` : "0 (YOLO Inactive)"}
            </span>
          </div>
        </div>
      </Card>

      {/* 4. Provenance Verified Sample Gallery */}
      <Card
        title="Provenance Verified Samples"
        badge={
          <span className="badge-green text-[9px]">
            {provenanceList.length} ASSETS
          </span>
        }
      >
        <div className="space-y-2 p-1 max-h-48 overflow-y-auto">
          {provenanceList.map((sample) => {
            const isSelected = selectedSampleId === sample.id;
            return (
              <button
                key={sample.id}
                onClick={() => onSelectSample(sample)}
                className={`w-full text-left p-2 rounded border transition text-[11px] ${
                  isSelected
                    ? "border-cyan-400 bg-cyan-950/40 text-white"
                    : "border-scada-border bg-slate-950 hover:bg-slate-900 text-slate-300"
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-bold truncate max-w-[190px]">{sample.title}</span>
                  <span className="badge-cyan text-[8px]">{sample.type}</span>
                </div>
                <div className="text-[10px] text-scada-muted mt-0.5 flex items-center justify-between">
                  <span>Lic: {sample.license}</span>
                  <span>{sample.resolution}</span>
                </div>
              </button>
            );
          })}
        </div>
      </Card>

      {/* 5. Terminal Execution Log */}
      <Card
        title="Live Perception Audit Log"
        badge={
          <span className="badge-cyan text-[9px] flex items-center gap-1">
            <Terminal size={9} />
            STDERR/OUT
          </span>
        }
      >
        <div className="bg-black/60 rounded-lg p-2.5 font-mono text-[10px] text-slate-300 max-h-40 overflow-y-auto space-y-1 border border-slate-800">
          {logs.length === 0 ? (
            <p className="text-slate-500 italic">No inference events executed yet...</p>
          ) : (
            logs.map((log, idx) => (
              <div key={idx} className="leading-tight text-slate-400">
                <span className="text-cyan-400">&gt; </span>
                {log}
              </div>
            ))
          )}
        </div>
      </Card>
    </div>
  );
}
