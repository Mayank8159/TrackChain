// Inference Execution Engine with Drag-and-Drop Upload & DEMO Simulation Fallback (tc.v1).

"use client";

import React, { useRef, useState } from "react";
import { UploadCloud, FileImage, Sparkles, AlertTriangle, ArrowRight, ScanLine } from "lucide-react";
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

  const compressAndResizeImage = (file: File): Promise<{ base64Data: string; dataUrl: string }> => {
    return new Promise((resolve, reject) => {
      const img = new Image();
      const objectUrl = URL.createObjectURL(file);

      img.onload = () => {
        URL.revokeObjectURL(objectUrl);
        const maxW = 640;
        const maxH = 480;
        let w = img.width;
        let h = img.height;

        if (w > maxW || h > maxH) {
          const ratio = Math.min(maxW / w, maxH / h);
          w = Math.max(1, Math.round(w * ratio));
          h = Math.max(1, Math.round(h * ratio));
        }

        const canvas = document.createElement("canvas");
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext("2d");
        if (!ctx) {
          reject(new Error("Unable to initialize canvas 2D rendering context"));
          return;
        }

        ctx.drawImage(img, 0, 0, w, h);
        const dataUrl = canvas.toDataURL("image/jpeg", 0.8);
        const base64Data = dataUrl.replace(/^data:image\/[a-z]+;base64,/, "");
        resolve({ base64Data, dataUrl });
      };

      img.onerror = () => {
        URL.revokeObjectURL(objectUrl);
        reject(new Error("Failed to load image into DOM"));
      };

      img.src = objectUrl;
    });
  };

  const processImageFile = async (file: File) => {
    // 1. Enforce 10MB limit
    if (file.size > 10 * 1024 * 1024) {
      showToast({
        type: "error",
        title: "File Exceeds Size Limit",
        description: `Selected file is ${(file.size / (1024 * 1024)).toFixed(1)}MB. Maximum allowed payload is 10.0MB.`,
      });
      return;
    }

    if (!file.type.startsWith("image/")) {
      showToast({
        type: "error",
        title: "Invalid File Format",
        description: "Please upload a valid JPEG, PNG, or WebP track image.",
      });
      return;
    }

    onInferenceStart();

    try {
      const { base64Data, dataUrl } = await compressAndResizeImage(file);
      await executeInference(base64Data, dataUrl);
    } catch (err: any) {
      onInferenceError(err);
      showToast({
        type: "error",
        title: "Image Preprocessing Failed",
        description: err?.message || "Unable to optimize image for inference pipeline.",
      });
    }
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
        vision_status: resp.vision_status || "OK",
        vision_confidence_score: resp.vision_confidence_score ?? 1.0,
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
    <label
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragOver(true);
      }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={handleDrop}
      className={`relative block w-full h-56 border-2 border-dashed transition-all cursor-pointer group overflow-hidden bg-slate-950/40 rounded-xl ${
        isDragOver
          ? "border-cyan-400 bg-cyan-950/30"
          : "border-slate-800 hover:border-cyan-500/80"
      }`}
    >
      {/* Scanner Laser Line Animation */}
      <div className="absolute inset-x-0 top-0 h-0.5 bg-cyan-400 shadow-[0_0_15px_#06B6D4] animate-scan-line opacity-0 group-hover:opacity-100 transition-opacity" />

      <div className="absolute inset-0 flex flex-col items-center justify-center p-4 text-center">
        <div className="w-12 h-12 mb-3 text-slate-500 group-hover:text-cyan-400 transition-colors flex items-center justify-center">
          <ScanLine className="w-10 h-10" strokeWidth={1.5} />
        </div>
        <p className="text-xs font-mono font-bold uppercase tracking-widest text-slate-300 group-hover:text-cyan-300 transition-colors">
          Drop Frame for YOLOv8n Optical Inference
        </p>
        <p className="text-[10px] font-mono text-slate-500 mt-2">
          Max 10MB • Auto-Resized & Compressed to 640×480
        </p>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={(e) => {
          if (e.target.files && e.target.files.length > 0) {
            processImageFile(e.target.files[0]);
          }
        }}
        className="sr-only"
      />
    </label>
  );
}
