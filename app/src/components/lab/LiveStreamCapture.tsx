// Real-Time Local Camera Stream Capture for Continuous Edge Inference Testing (tc.v1).

"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import { Camera, CameraOff, Video, AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";

interface LiveStreamCaptureProps {
  isActive: boolean;
  onFrameCaptured: (base64Data: string, previewUrl: string) => void;
  onFpsUpdate?: (fps: number) => void;
}

export function LiveStreamCapture({
  isActive,
  onFrameCaptured,
  onFpsUpdate,
}: LiveStreamCaptureProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const frameCountRef = useRef(0);
  const lastFpsTimeRef = useRef(Date.now());

  const [hasPermission, setHasPermission] = useState<boolean | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const { showToast } = useToast();

  const stopStream = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  }, []);

  const startStream = useCallback(async () => {
    stopStream();
    setErrorMsg(null);

    try {
      if (!navigator?.mediaDevices?.getUserMedia) {
        throw new Error("Camera API not supported in this browser environment.");
      }

      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 640 },
          height: { ideal: 480 },
          facingMode: "environment",
        },
        audio: false,
      });

      streamRef.current = mediaStream;
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
        await videoRef.current.play();
      }

      setHasPermission(true);
      showToast({
        type: "success",
        title: "Optical Stream Active",
        description: "Local camera connected. Capturing frames at 2.0 FPS for inference.",
      });

      // Capture frame loop throttled to 2 FPS (500ms)
      lastFpsTimeRef.current = Date.now();
      frameCountRef.current = 0;

      intervalRef.current = setInterval(() => {
        if (!videoRef.current || !canvasRef.current) return;

        const video = videoRef.current;
        const canvas = canvasRef.current;
        if (video.readyState < 2) return;

        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        canvas.width = 640;
        canvas.height = 480;
        ctx.drawImage(video, 0, 0, 640, 480);

        const dataUrl = canvas.toDataURL("image/jpeg", 0.7);
        const base64 = dataUrl.replace(/^data:image\/[a-z]+;base64,/, "");

        onFrameCaptured(base64, dataUrl);

        // Rolling FPS tracking
        frameCountRef.current += 1;
        const now = Date.now();
        const elapsed = (now - lastFpsTimeRef.current) / 1000;
        if (elapsed >= 1.0) {
          const fps = Math.round((frameCountRef.current / elapsed) * 10) / 10;
          onFpsUpdate?.(fps);
          frameCountRef.current = 0;
          lastFpsTimeRef.current = now;
        }
      }, 500);
    } catch (err: any) {
      setHasPermission(false);
      const msg = err?.message || "Could not access optical camera sensor.";
      setErrorMsg(msg);
      showToast({
        type: "error",
        title: "Camera Access Error",
        description: msg,
      });
    }
  }, [stopStream, onFrameCaptured, onFpsUpdate, showToast]);

  useEffect(() => {
    if (isActive) {
      startStream();
    } else {
      stopStream();
    }

    return () => {
      stopStream();
    };
  }, [isActive, startStream, stopStream]);

  return (
    <div className="hidden">
      {/* Hidden processing video and canvas elements */}
      <video ref={videoRef} playsInline muted autoPlay className="w-0 h-0" />
      <canvas ref={canvasRef} className="w-0 h-0" />

      {errorMsg && (
        <div className="p-3 bg-red-500/20 border border-red-500 text-red-300 rounded text-xs flex items-center gap-2">
          <AlertTriangle size={14} />
          <span>{errorMsg}</span>
        </div>
      )}
    </div>
  );
}
