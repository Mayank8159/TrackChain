// Plays a segment from a presigned S3 URL; emits currentTime for sync.

"use client";

import React, { useRef, useState, useEffect } from "react";
import { cn } from "../../lib/utils";

interface VideoPlayerProps {
  src?: string;
  currentTime?: number;
  onTimeUpdate?: (time: number) => void;
  className?: string;
}

export function VideoPlayer({
  src,
  currentTime,
  onTimeUpdate,
  className,
}: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);

  useEffect(() => {
    if (
      videoRef.current &&
      currentTime !== undefined &&
      Math.abs(videoRef.current.currentTime - currentTime) > 0.5
    ) {
      videoRef.current.currentTime = currentTime;
    }
  }, [currentTime]);

  const handleTimeUpdate = () => {
    if (videoRef.current && onTimeUpdate) {
      onTimeUpdate(videoRef.current.currentTime);
    }
  };

  return (
    <div
      className={cn(
        "relative aspect-video w-full rounded-lg border border-scada-border bg-black/80 overflow-hidden flex flex-col items-center justify-center scada-grid",
        className
      )}
    >
      {src ? (
        <video
          ref={videoRef}
          src={src}
          className="h-full w-full object-contain"
          onTimeUpdate={handleTimeUpdate}
          onPlay={() => setIsPlaying(true)}
          onPause={() => setIsPlaying(false)}
          controls
        />
      ) : (
        /* Synthetic Video Stream Simulation */
        <div className="flex flex-col items-center gap-2 p-6 text-center font-mono">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-scada-red animate-pulse" />
            <span className="text-xs font-bold uppercase text-scada-text tracking-wider">
              Optical Rail Scanner Stream (1080p60)
            </span>
          </div>
          <p className="text-[10px] text-scada-muted max-w-sm">
            Live edge video segment feed connected to MinIO S3 media bucket
          </p>
        </div>
      )}

      {/* Crosshair Overlay */}
      <div className="pointer-events-none absolute inset-0 flex items-center justify-center opacity-30">
        <div className="h-8 w-px bg-scada-cyan" />
        <div className="absolute h-px w-8 bg-scada-cyan" />
      </div>
    </div>
  );
}
