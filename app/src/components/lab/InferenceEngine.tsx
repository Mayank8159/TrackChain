// Inference Execution Engine with Drag-and-Drop Upload & DEMO Simulation Fallback (tc.v1).

"use client";

import React, { useRef, useState } from "react";
import { UploadCloud, FileImage, Sparkles, AlertTriangle, ArrowRight } from "lucide-react";
import { useModeStore } from "@/stores/mode-store";
import { useToast } from "@/components/ui/Toast";
import { api } from "@/lib/api";
import type { InferenceResult, ImageProvenance } from "@/lib/types";

interface InferenceEngineProps {
  onInferenceStart: () => void;
  onInferenceComplete: (
    result: InferenceResult,
    imagePreview: string,
    isSimulated: boolean
  ) => void;
  onInferenceError: (err: any) => void;
}

export function InferenceEngine({
  onInferenceStart,
  onInferenceComplete,
  onInferenceError,
}: InferenceEngineProps) {
  const { mode } = useModeStore();
  const { showToast } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const processImageFile = async (file: File) => {
    // 1. Enforce 5MB limit
    if (file.size > 5 * 1024 * 1024) {
      showToast({
        type: "error",
        title: "File Exceeds Size Limit",
        description: `Selected file is ${(file.size / (1024 * 1024)).toFixed(1)}MB. Maximum allowed payload is 5.0MB.`,
      });
      return;
    }

    if (!file.type.startsWith("image/")) {
      showToast({
        type: "error",
        title: "Invalid File Format",
        description: "Please upload a valid JPEG, PNG, or SVG track image.",
      });
      return;
    }

    onInferenceStart();

    const reader = new FileReader();
    reader.onload = async (e) => {
      const dataUrl = e.target?.result as string;
      const base64Data = dataUrl.replace(/^data:image\/[a-z]+;base64,/, "");

      await executeInference(base64Data, dataUrl);
    };

    reader.onerror = (err) => {
      onInferenceError(err);
      showToast({
        type: "error",
        title: "File Read Failed",
        description: "Unable to read raw image bytes from filesystem.",
      });
    };

    reader.readAsDataURL(file);
  };

  const executeInference = async (base64Data: string, previewUrl: string) => {
    // Attempt real ML inference first via FastAPI /process-frame
    try {
      const resp = await api.request<any>("/process-frame", {
        method: "POST",
        body: JSON.stringify({
          camera_id: "lab-bench-01",
          frame: base64Data,
        }),
      });

      // Split raw Hough lines into rails vs sleepers based on angle
      const rawLines = resp.lines || [];
      const rails = rawLines.filter((l: any) => Math.abs(l.angle_deg || 0) < 30 || Math.abs(l.angle_deg || 0) > 150);
      const sleepers = rawLines.filter((l: any) => Math.abs(l.angle_deg || 0) >= 30 && Math.abs(l.angle_deg || 0) <= 150);

      const realResult: InferenceResult = {
        trace_id: `trc-proc-${Date.now().toString(36)}`,
        inference_ms: resp.processing_ms || resp.processingMs || 42.0,
        image_width: resp.resolution?.[0] || 640,
        image_height: resp.resolution?.[1] || 480,
        rails: rails.map((r: any) => ({
          x1: r.x1,
          y1: r.y1,
          x2: r.x2,
          y2: r.y2,
          theta_deg: r.angle_deg || 0,
        })),
        sleepers: sleepers.map((s: any) => ({
          x1: s.x1,
          y1: s.y1,
          x2: s.x2,
          y2: s.y2,
          theta_deg: s.angle_deg || 90,
        })),
        yolo_boxes: resp.yolo_boxes || [],
        yolo_weights_loaded: resp.yolo_weights_loaded !== false,
        status: "ok",
      };

      onInferenceComplete(realResult, previewUrl, false);
      return;
    } catch (err) {
      if (mode === "REAL") {
        onInferenceError(err);
        showToast({
          type: "error",
          title: "Inference Server Error",
          description: "FastAPI /process-frame backend failed to process image.",
        });
        return;
      }
    }

    // Fallback if offline
    const simulatedResult: InferenceResult = {
      trace_id: `trc-sim-${Date.now().toString(36)}`,
      inference_ms: 38.5,
      image_width: 640,
      image_height: 480,
      rails: [
        { x1: 194, y1: 0, x2: 194, y2: 480, theta_deg: 0.0, length: 480 },
        { x1: 446, y1: 0, x2: 446, y2: 480, theta_deg: 0.0, length: 480 },
      ],
      sleepers: [
        { x1: 120, y1: 55, x2: 520, y2: 55, theta_deg: 90.0, length: 400 },
        { x1: 120, y1: 110, x2: 520, y2: 110, theta_deg: 90.0, length: 400 },
        { x1: 120, y1: 165, x2: 520, y2: 165, theta_deg: 90.0, length: 400 },
        { x1: 120, y1: 220, x2: 520, y2: 220, theta_deg: 90.0, length: 400 },
        { x1: 120, y1: 275, x2: 520, y2: 275, theta_deg: 90.0, length: 400 },
        { x1: 120, y1: 330, x2: 520, y2: 330, theta_deg: 90.0, length: 400 },
        { x1: 120, y1: 385, x2: 520, y2: 385, theta_deg: 90.0, length: 400 },
        { x1: 120, y1: 440, x2: 520, y2: 440, theta_deg: 90.0, length: 400 },
      ],
      yolo_boxes: [
        {
          class: "missing_fastener",
          confidence: 0.94,
          xmin: 160,
          ymin: 180,
          xmax: 225,
          ymax: 235,
        },
      ],
      yolo_weights_loaded: true,
      status: "ok",
    };

    onInferenceComplete(simulatedResult, previewUrl, true);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      processImageFile(e.dataTransfer.files[0]);
    }
  };

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragOver(true);
      }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={handleDrop}
      onClick={() => fileInputRef.current?.click()}
      className={`rounded-xl border-2 border-dashed p-6 text-center cursor-pointer transition flex flex-col items-center justify-center gap-2 ${
        isDragOver
          ? "border-cyan-400 bg-cyan-950/20"
          : "border-scada-border hover:border-slate-600 bg-slate-900/60"
      }`}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={(e) => {
          if (e.target.files && e.target.files.length > 0) {
            processImageFile(e.target.files[0]);
          }
        }}
        className="hidden"
      />

      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-800 text-cyan-400">
        <UploadCloud size={20} />
      </div>

      <div className="space-y-0.5 font-mono">
        <p className="text-xs font-bold text-white">
          Drop track image here or <span className="text-cyan-400 underline">browse</span>
        </p>
        <p className="text-[10px] text-scada-muted">
          Supports JPEG, PNG, SVG up to 5MB · Base64 JPEG Ingest
        </p>
      </div>
    </div>
  );
}
