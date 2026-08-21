// State-of-the-Art Model Test Bench & Computer Vision AI Validation Lab (tc.v1).

"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  FlaskConical,
  Video,
  Image as ImageIcon,
  RotateCcw,
  Sparkles,
  Layers,
  Activity,
  Cpu,
} from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/Button";
import { ImageViewport } from "@/components/lab/ImageViewport";
import { InferenceEngine } from "@/components/lab/InferenceEngine";
import { LiveStreamCapture } from "@/components/lab/LiveStreamCapture";
import { TelemetrySidebar } from "@/components/lab/TelemetrySidebar";
import { useModeStore } from "@/stores/mode-store";
import { useToast } from "@/components/ui/Toast";
import type { InferenceResult, ImageProvenance } from "@/lib/types";

const INITIAL_PROVENANCE: ImageProvenance[] = [
  {
    id: "sample-track-01",
    title: "Nominal Tangent Track (NDLS)",
    url: "/samples/sample-track-01.svg",
    source: "Northern Railway Maintenance Div",
    license: "RDSO Internal / Open Data",
    type: "SYNTHETIC",
    description: "Standard gauge 1676mm concrete sleeper tangent track.",
    resolution: "640x480",
  },
  {
    id: "sample-track-02",
    title: "Missing Fastener & Dislodgement",
    url: "/samples/sample-track-02.svg",
    source: "TrackChain Synthetic Anomaly Engine",
    license: "Apache-2.0",
    type: "SYNTHETIC",
    description: "Left rail fastener clip missing at Sleeper #3.",
    resolution: "640x480",
  },
  {
    id: "sample-track-03",
    title: "Surface Spalling Anomaly",
    url: "/samples/sample-track-03.svg",
    source: "TrackChain Synthetic Anomaly Engine",
    license: "Apache-2.0",
    type: "SYNTHETIC",
    description: "Rolling contact fatigue along the gauge corner.",
    resolution: "640x480",
  },
  {
    id: "sample-track-04",
    title: "Severe Longitudinal Crack",
    url: "/samples/sample-track-04.svg",
    source: "TrackChain Synthetic Anomaly Engine",
    license: "Apache-2.0",
    type: "SYNTHETIC",
    description: "Transverse railhead fracture at sleeper transition.",
    resolution: "640x480",
  },
];

export default function ModelTestBenchPage() {
  const { mode } = useModeStore();
  const { showToast } = useToast();

  const [activeTab, setActiveTab] = useState<"single" | "stream">("single");
  const [currentImageSrc, setCurrentImageSrc] = useState<string | null>(
    INITIAL_PROVENANCE[0].url
  );
  const [selectedSampleId, setSelectedSampleId] = useState<string | null>(
    INITIAL_PROVENANCE[0].id
  );
  const [inferenceResult, setInferenceResult] = useState<InferenceResult | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isSimulated, setIsSimulated] = useState<boolean>(mode === "DEMO");
  const [fps, setFps] = useState<number>(0);
  const [logs, setLogs] = useState<string[]>([]);

  const appendLog = useCallback((message: string) => {
    const timestamp = new Date().toLocaleTimeString("en-IN", { hour12: false });
    setLogs((prev) => [`[${timestamp}] ${message}`, ...prev.slice(0, 49)]);
  }, []);

  const handleInferenceStart = () => {
    setIsLoading(true);
  };

  const handleInferenceComplete = (
    result: InferenceResult,
    imagePreview: string,
    simulated: boolean
  ) => {
    setIsLoading(false);
    setInferenceResult(result);
    setCurrentImageSrc(imagePreview);
    setIsSimulated(simulated);

    const rails = result.rails?.length || 0;
    const sleepers = result.sleepers?.length || 0;
    const boxes = result.yolo_boxes?.length || 0;
    appendLog(
      `${result.inference_ms.toFixed(1)}ms | ${rails} Rails | ${sleepers} Sleepers | ${boxes} Fastener Faults`
    );
  };

  const handleInferenceError = (err: any) => {
    setIsLoading(false);
    appendLog(`ERROR: ${err?.message || "Perception pipeline failure"}`);
  };

  const handleSelectSample = (sample: ImageProvenance) => {
    setSelectedSampleId(sample.id);
    setCurrentImageSrc(sample.url);
    setIsLoading(true);

    // Run deterministic perception simulation for sample
    setTimeout(() => {
      setIsLoading(false);
      const isAnomaly = sample.id === "sample-track-02" || sample.id === "sample-track-04";
      const sampleResult: InferenceResult = {
        trace_id: `trc-spl-${Math.random().toString(36).substring(2, 9)}`,
        inference_ms: 34.2,
        image_width: 640,
        image_height: 480,
        rails: [
          { x1: 194, y1: 0, x2: 194, y2: 480, theta_deg: 0.0, length: 480 },
          { x1: 446, y1: 0, x2: 446, y2: 480, theta_deg: 0.0, length: 480 },
        ],
        sleepers: [
          { x1: 120, y1: 55, x2: 520, y2: 55, theta_deg: 90.0, length: 400 },
          { x1: 120, y1: 125, x2: 520, y2: 125, theta_deg: 90.0, length: 400 },
          { x1: 120, y1: 195, x2: 520, y2: 195, theta_deg: 90.0, length: 400 },
          { x1: 120, y1: 265, x2: 520, y2: 265, theta_deg: 90.0, length: 400 },
          { x1: 120, y1: 335, x2: 520, y2: 335, theta_deg: 90.0, length: 400 },
          { x1: 120, y1: 405, x2: 520, y2: 405, theta_deg: 90.0, length: 400 },
        ],
        yolo_boxes: isAnomaly
          ? [
              {
                class: sample.id === "sample-track-02" ? "missing_fastener" : "rail_crack",
                confidence: 0.94,
                xmin: sample.id === "sample-track-02" ? 158 : 175,
                ymin: sample.id === "sample-track-02" ? 180 : 265,
                xmax: sample.id === "sample-track-02" ? 228 : 210,
                ymax: sample.id === "sample-track-02" ? 235 : 325,
              },
            ]
          : [],
        yolo_weights_loaded: true,
        status: "ok",
      };

      setInferenceResult(sampleResult);
      setIsSimulated(true);
      appendLog(
        `Loaded Provenance Sample: ${sample.title} (${sampleResult.inference_ms}ms, ${sampleResult.rails.length} Rails)`
      );
    }, 120);
  };

  // Initial trigger
  useEffect(() => {
    handleSelectSample(INITIAL_PROVENANCE[0]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleFrameCaptured = (base64Data: string, previewUrl: string) => {
    setCurrentImageSrc(previewUrl);

    // Fast simulated response on webcam stream
    const simResult: InferenceResult = {
      trace_id: `trc-live-${Math.random().toString(36).substring(2, 9)}`,
      inference_ms: 28.5 + (Math.random() * 8),
      image_width: 640,
      image_height: 480,
      rails: [
        { x1: 180, y1: 0, x2: 180, y2: 480, theta_deg: 0.0, length: 480 },
        { x1: 460, y1: 0, x2: 460, y2: 480, theta_deg: 0.0, length: 480 },
      ],
      sleepers: [
        { x1: 100, y1: 100, x2: 540, y2: 100, theta_deg: 90.0, length: 440 },
        { x1: 100, y1: 220, x2: 540, y2: 220, theta_deg: 90.0, length: 440 },
        { x1: 100, y1: 340, x2: 540, y2: 340, theta_deg: 90.0, length: 440 },
      ],
      yolo_boxes: [],
      yolo_weights_loaded: false,
      status: "ok",
    };

    setInferenceResult(simResult);
    setIsSimulated(true);
  };

  return (
    <div className="p-4 lg:p-6 flex flex-col gap-6 max-w-7xl mx-auto w-full">
      {/* 1. Page Header */}
      <PageHeader
        title="Model Test Bench & AI Perception Lab"
        description="Interactive computer vision verification, Hough rail geometry extraction, YOLOv8 explainability & real-time edge webcam inference"
        breadcrumbs={[{ label: "AI Lab" }]}
        actions={
          <div className="flex items-center gap-2">
            {/* Mode Switcher */}
            <div className="flex items-center bg-slate-900 border border-scada-border rounded-lg p-0.5">
              <button
                onClick={() => {
                  setActiveTab("single");
                  setFps(0);
                }}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-mono font-bold transition ${
                  activeTab === "single"
                    ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                    : "text-scada-muted hover:text-white"
                }`}
              >
                <ImageIcon size={13} />
                Single Image
              </button>
              <button
                onClick={() => {
                  setActiveTab("stream");
                }}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-mono font-bold transition ${
                  activeTab === "stream"
                    ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                    : "text-scada-muted hover:text-white"
                }`}
              >
                <Video size={13} className={activeTab === "stream" ? "animate-pulse text-emerald-400" : ""} />
                Live Stream (Webcam)
              </button>
            </div>

            <Button
              variant="secondary"
              size="md"
              onClick={() => handleSelectSample(INITIAL_PROVENANCE[0])}
              className="text-xs font-mono"
            >
              <RotateCcw size={13} className="mr-1.5" />
              Reset Lab
            </Button>
          </div>
        }
      />

      {/* 2. Main IDE 2-Column Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Viewport & Ingestion Dropzone (7 cols) */}
        <div className="lg:col-span-7 flex flex-col gap-4">
          <ImageViewport
            imageSrc={currentImageSrc}
            inferenceResult={inferenceResult}
            isLoading={isLoading}
            isSimulated={isSimulated}
          />

          {/* Dropzone Upload Trigger (Single Image Mode) */}
          {activeTab === "single" ? (
            <InferenceEngine
              onInferenceStart={handleInferenceStart}
              onInferenceComplete={handleInferenceComplete}
              onInferenceError={handleInferenceError}
            />
          ) : (
            <div className="p-4 rounded-xl border border-emerald-500/40 bg-emerald-950/20 text-emerald-300 font-mono text-xs flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Video size={16} className="text-emerald-400 animate-pulse" />
                <span>Real-Time Webcam Pipeline Active (Capturing at 2.0 FPS)</span>
              </div>
              <span className="badge-green text-[10px]">LIVE INGEST</span>
            </div>
          )}

          {/* Live Stream Sensor Subsystem (Mounted in Stream Mode) */}
          <LiveStreamCapture
            isActive={activeTab === "stream"}
            onFrameCaptured={handleFrameCaptured}
            onFpsUpdate={(newFps) => setFps(newFps)}
          />
        </div>

        {/* Right Column: Telemetry & Provenance Sidebar (5 cols) */}
        <div className="lg:col-span-5">
          <TelemetrySidebar
            result={inferenceResult}
            fps={fps}
            logs={logs}
            provenanceList={INITIAL_PROVENANCE}
            selectedSampleId={selectedSampleId}
            onSelectSample={handleSelectSample}
          />
        </div>
      </div>
    </div>
  );
}
