// The Hero Screen: Synchronized Video Player, Multi-Channel Telemetry, and Defect Inspector (tc.v1).

"use client";

import React, { useState, useEffect, useRef, Suspense } from "react";
import { useParams, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Gauge,
  Zap,
  Activity,
  AlertTriangle,
  Clock,
  Video,
  LineChart,
  Eye,
  Crosshair,
  SlidersHorizontal,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { SessionStatusBadge } from "@/components/sessions/SessionStatusBadge";
import { VideoPlayer, VideoPlayerHandle } from "@/components/video/VideoPlayer";
import { TelemetryChart } from "@/components/telemetry/TelemetryChart";
import { EvidenceModal } from "@/components/video/EvidenceModal";
import { DataError } from "@/components/ui/DataError";
import { useModeStore } from "@/stores/mode-store";
import { useSession } from "@/hooks/useSession";
import { useTelemetry } from "@/hooks/useTelemetry";
import { useDefects } from "@/hooks/useDefects";
import { usePlaybackSync } from "@/hooks/usePlaybackSync";
import { formatChainage, formatTimestamp, formatConfidence, formatDuration } from "@/lib/format";
import type { DefectEvent } from "@/lib/types";

function LiveMissionTimer({ startTime }: { startTime: string }) {
  const [elapsedSec, setElapsedSec] = useState<number>(0);

  useEffect(() => {
    const calcElapsed = () => {
      const startMs = new Date(startTime).getTime();
      const nowMs = Date.now();
      setElapsedSec(Math.max(0, Math.floor((nowMs - startMs) / 1000)));
    };

    calcElapsed();
    const interval = setInterval(calcElapsed, 1000);
    return () => clearInterval(interval);
  }, [startTime]);

  return (
    <div className="flex items-center gap-2 rounded-control bg-emerald-500/10 border border-emerald-500/30 px-3 py-1 text-emerald-400 font-mono text-xs">
      <Clock size={13} className="animate-spin" />
      <span className="font-bold tracking-wider">
        LIVE DURATION: {formatDuration(elapsedSec)}
      </span>
    </div>
  );
}

function SessionInspectionHeroContent() {
  const params = useParams();
  const searchParams = useSearchParams();
  const { mode } = useModeStore();
  const sessionId = (params?.id as string) || "ses-delhi-agra-001";
  const initialSeek = searchParams?.get("seek");

  const videoRef = useRef<VideoPlayerHandle | null>(null);
  const videoCardRef = useRef<HTMLDivElement | null>(null);

  const sessionQuery = useSession(sessionId);
  const telemetryQuery = useTelemetry(sessionId);
  const defectsQuery = useDefects();

  const session = sessionQuery.data;
  const telemetry = telemetryQuery.data || [];
  const allDefects = defectsQuery.defects || [];

  const isRealError = mode === "REAL" && (sessionQuery.isError || telemetryQuery.isError);

  // Filter defects for this session or fallback to mock items
  const sessionDefects = allDefects.filter(
    (d) => d.sessionId === sessionId || d.sessionId === "ses-delhi-agra-001"
  );

  const [evidenceDefect, setEvidenceDefect] = useState<DefectEvent | null>(null);
  const [activeMetricTab, setActiveMetricTab] = useState<
    "vibrationRms" | "twistMmPerM" | "trackGaugeMm" | "speedKmh" | "cantMm"
  >("vibrationRms");

  // Bi-directional Video <-> Telemetry synchronization engine
  const sync = usePlaybackSync({
    telemetryData: telemetry,
    videoDurationSec: 60,
    videoRef,
  });

  // Automatically seek to requested video timestamp if passed via ?seek=...
  useEffect(() => {
    if (initialSeek) {
      const seekSec = parseFloat(initialSeek);
      if (!isNaN(seekSec)) {
        sync.seekToTime(seekSec);
        if (videoCardRef.current) {
          videoCardRef.current.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      }
    }
  }, [initialSeek]);

  const isLive = session?.status === "active" || session?.status === "running";

  // Crucial Interaction: Seek video & smoothly scroll to player when a defect is inspected
  const handleInspectDefect = (defect: DefectEvent) => {
    const targetSec = defect.videoTimestampSec || 0;
    sync.seekToTime(targetSec);

    if (videoCardRef.current) {
      videoCardRef.current.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  };

  if (isRealError) {
    return (
      <div className="p-4 lg:p-6 max-w-7xl mx-auto w-full">
        <DataError
          title="Inspection Session Telemetry Offline"
          message={`Failed to stream video metadata and 100 Hz sensor telemetry for session ${sessionId} from backend.`}
          onRetry={() => {
            sessionQuery.refetch();
            telemetryQuery.refetch();
          }}
        />
      </div>
    );
  }

  return (
    <div className="p-4 lg:p-6 flex flex-col gap-6 max-w-7xl mx-auto w-full">
      {/* 1. Header & Navigation Backlink */}
      <div className="flex flex-col gap-3 border-b border-scada-border pb-4">
        <Link
          href="/sessions"
          className="inline-flex items-center gap-1.5 text-xs font-mono text-scada-accent hover:underline font-semibold w-fit"
        >
          <ArrowLeft size={14} />
          <span>Back to Sessions Registry</span>
        </Link>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold font-mono tracking-wider text-white">
                {session?.id || sessionId}
              </h1>
              <SessionStatusBadge status={session?.status || "completed"} />
              {isLive && session?.startTime && (
                <LiveMissionTimer startTime={session.startTime} />
              )}
            </div>
            <p className="text-xs font-mono text-scada-muted mt-1">
              {session?.name} — {session?.trackSection}
            </p>
          </div>

          <div className="flex items-center gap-3">
            {/* Live Playhead Telemetry HUD Indicator */}
            <div className="flex items-center gap-2 rounded-control bg-slate-900 border border-scada-border px-3 py-1.5 font-mono text-xs">
              <Crosshair size={14} className="text-cyan-400 animate-pulse" />
              <span className="text-scada-muted">PLAYHEAD CHAINAGE:</span>
              <strong className="text-cyan-400">
                {formatChainage(sync.currentChainageM)}
              </strong>
            </div>

            <Link href="/reports">
              <Button variant="outline" size="md">
                Export Run Report
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* 2. Mission Metadata Summary Cards (4 Columns) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="scada-card p-4 border border-scada-border">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono font-bold uppercase text-scada-muted">
              Distance Covered
            </span>
            <Gauge size={16} className="text-cyan-400" />
          </div>
          <p className="text-2xl font-mono font-bold text-white mt-1">
            {session?.totalDistanceKm ? session.totalDistanceKm.toFixed(1) : "140.0"}{" "}
            <span className="text-xs text-scada-muted">km</span>
          </p>
          <p className="text-[10px] font-mono text-scada-muted mt-1">
            Track Section: {session?.trackId || "IR-NR-01"}
          </p>
        </div>

        <div className="scada-card p-4 border border-scada-border">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono font-bold uppercase text-scada-muted">
              Operating Speed
            </span>
            <Zap size={16} className="text-amber-400" />
          </div>
          <p className="text-2xl font-mono font-bold text-white mt-1">
            110.5 <span className="text-xs text-scada-muted">km/h</span>
          </p>
          <p className="text-[10px] font-mono text-scada-muted mt-1">
            Max Corridor Speed: 130 km/h
          </p>
        </div>

        <div className="scada-card p-4 border border-scada-border">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono font-bold uppercase text-scada-muted">
              Average TQI Score
            </span>
            <Activity size={16} className="text-emerald-400" />
          </div>
          <p className="text-2xl font-mono font-bold text-emerald-400 mt-1">
            88.4 <span className="text-xs text-scada-muted">/ 100</span>
          </p>
          <p className="text-[10px] font-mono text-scada-muted mt-1">
            RDSO CTI Standard: Category A
          </p>
        </div>

        <div className="scada-card p-4 border border-scada-border">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono font-bold uppercase text-scada-muted">
              Flagged Defects
            </span>
            <AlertTriangle size={16} className="text-red-400" />
          </div>
          <p className="text-2xl font-mono font-bold text-red-400 mt-1">
            {sessionDefects.length}{" "}
            <span className="text-xs text-scada-muted">anomalies</span>
          </p>
          <p className="text-[10px] font-mono text-scada-muted mt-1">
            {sessionDefects.filter((d) => d.severity === "critical").length} Critical IAL
          </p>
        </div>
      </div>

      {/* 3. HERO SECTION: Video Player (2/3) + Defect List (1/3) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Top-Left: Synchronized HLS Video Player */}
        <div ref={videoCardRef} className="lg:col-span-2">
          <Card
            title="Synchronized Optical Video Stream"
            badge={<span className="badge-cyan text-[10px]">HLS 1080p60</span>}
            actions={
              <div className="flex items-center gap-2 font-mono text-[11px] text-scada-muted">
                <span>Playhead:</span>
                <strong className="text-cyan-400">
                  {formatDuration(Math.floor(sync.currentTime))}
                </strong>
              </div>
            }
          >
            <VideoPlayer
              ref={videoRef}
              initialTime={0}
              duration={60}
              onTimeUpdate={sync.handleVideoTimeUpdate}
              defects={sessionDefects}
              streamName="CAM-BOGIE-LEFT (1080p60)"
            />
          </Card>
        </div>

        {/* Top-Right: Defects Detected in Run */}
        <div className="flex flex-col gap-4">
          <Card
            title={`Defects in Run (${sessionDefects.length})`}
            badge={
              <span className="badge-red text-[10px]">
                {sessionDefects.filter((d) => d.severity === "critical").length} CRITICAL
              </span>
            }
            className="h-full flex flex-col justify-between"
          >
            <div className="flex-1 overflow-y-auto max-h-[380px] divide-y divide-scada-border/60">
              {sessionDefects.map((d) => (
                <div
                  key={d.id}
                  className="py-3 px-1 flex flex-col gap-2 transition-colors hover:bg-slate-800/30"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <SeverityBadge severity={d.severity} size="sm" />
                      <span className="text-xs font-mono font-bold text-white uppercase">
                        {d.defectClass.replace("_", " ")}
                      </span>
                    </div>
                    <span className="text-[11px] font-mono text-cyan-400 font-bold">
                      {formatChainage(d.chainageM)}
                    </span>
                  </div>

                  <p className="text-[10px] font-mono text-scada-muted leading-tight">
                    {d.description || "Identified by automated AI inference pipeline."}
                  </p>

                  <div className="flex items-center justify-between mt-1 pt-1 border-t border-scada-border/40">
                    <span className="text-[10px] font-mono text-emerald-400">
                      Confidence: {formatConfidence(d.confidence)}
                    </span>

                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setEvidenceDefect(d)}
                        className="text-[10px] text-scada-muted hover:text-white"
                      >
                        <Eye size={12} className="mr-1" />
                        Evidence
                      </Button>

                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() => handleInspectDefect(d)}
                        className="text-[10px]"
                      >
                        Seek Video →
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-3 pt-2 border-t border-scada-border flex items-center justify-between text-[10px] font-mono text-scada-muted">
              <span>Click "Seek Video" to jump playhead</span>
              <Link href="/defects" className="text-scada-accent hover:underline">
                Registry →
              </Link>
            </div>
          </Card>
        </div>
      </div>

      {/* 4. BOTTOM SECTION: Multi-Channel Telemetry Waveform Suite */}
      <Card
        title="Synchronized EN 13848 Track Geometry & Multi-Channel Waveforms"
        badge={
          <span className="badge-cyan text-[10px]">
            {telemetry.length} SENSOR POINTS
          </span>
        }
        actions={
          <div className="flex items-center gap-1.5 font-mono text-xs">
            {(
              [
                { key: "vibrationRms", label: "Vibration RMS" },
                { key: "twistMmPerM", label: "Track Twist" },
                { key: "trackGaugeMm", label: "Track Gauge" },
                { key: "speedKmh", label: "Speed" },
                { key: "cantMm", label: "Cant" },
              ] as const
            ).map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveMetricTab(tab.key)}
                className={`px-2.5 py-1 rounded text-[11px] uppercase transition ${
                  activeMetricTab === tab.key
                    ? "bg-scada-accent/20 text-scada-accent border border-scada-accent font-bold"
                    : "bg-slate-900 text-scada-muted border border-scada-border hover:text-white"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        }
      >
        <div className="flex flex-col gap-4">
          <div className="text-[11px] font-mono text-scada-muted flex items-center justify-between bg-slate-900/60 p-2 rounded border border-scada-border">
            <span>
              Interactive Waveform: Click anywhere on the chart or drag the video scrubber to seek the playhead.
            </span>
            <span className="text-cyan-400 font-bold">
              Active Playhead: {formatChainage(sync.currentChainageM)}
            </span>
          </div>

          <TelemetryChart
            data={telemetry}
            metricKey={activeMetricTab}
            currentChainageM={sync.currentChainageM}
            defects={sessionDefects}
            height={220}
            onSeekChainage={sync.seekToChainage}
          />
        </div>
      </Card>

      {/* Evidence Snapshot Modal */}
      <EvidenceModal
        defect={evidenceDefect}
        isOpen={!!evidenceDefect}
        onClose={() => setEvidenceDefect(null)}
      />
    </div>
  );
}

export default function SessionInspectionHeroPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center font-mono text-scada-muted">Loading Inspection Session Workspace...</div>}>
      <SessionInspectionHeroContent />
    </Suspense>
  );
}
