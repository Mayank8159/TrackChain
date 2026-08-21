// High-performance HLS Video Player with custom SCADA controls and time scrubbing (tc.v1).

"use client";

import React, {
  useRef,
  useState,
  useEffect,
  forwardRef,
  useImperativeHandle,
  useCallback,
} from "react";
import Hls from "hls.js";
import {
  Play,
  Pause,
  RotateCcw,
  Maximize,
  Volume2,
  VolumeX,
  FastForward,
  Rewind,
  VideoOff,
  Crosshair,
  Flag,
} from "lucide-react";
import { formatDuration } from "../../lib/format";
import { cn } from "../../lib/utils";
import { BoundingBoxOverlay } from "./BoundingBoxOverlay";
import type { DefectEvent } from "../../lib/types";
import { useCollabStore } from "../../stores/collab-store";

export interface VideoPlayerHandle {
  seekTo: (seconds: number) => void;
  play: () => void;
  pause: () => void;
  getCurrentTime: () => number;
}

export interface VideoPlayerProps {
  src?: string;
  initialTime?: number;
  duration?: number;
  onTimeUpdate?: (timeSec: number) => void;
  onSeek?: (timeSec: number) => void;
  streamName?: string;
  fps?: number;
  defects?: DefectEvent[];
  className?: string;
}

export const VideoPlayer = forwardRef<VideoPlayerHandle, VideoPlayerProps>(
  function VideoPlayer(
    {
      src,
      initialTime = 0,
      duration: externalDuration = 60,
      onTimeUpdate,
      onSeek,
      streamName = "CAM-BOGIE-01 (1080p60)",
      fps = 60,
      defects,
      className,
    },
    ref
  ) {
    const videoRef = useRef<HTMLVideoElement | null>(null);
    const containerRef = useRef<HTMLDivElement | null>(null);
    const hlsRef = useRef<Hls | null>(null);

    const [isPlaying, setIsPlaying] = useState<boolean>(false);
    const [currentTime, setCurrentTime] = useState<number>(initialTime);
    const [duration, setDuration] = useState<number>(externalDuration);
    const [playbackRate, setPlaybackRate] = useState<number>(1);
    const [isMuted, setIsMuted] = useState<boolean>(true);
    const [hasError, setHasError] = useState<boolean>(false);
    const [isSyntheticMode, setIsSyntheticMode] = useState<boolean>(!src);

    const collabStore = useCollabStore();
    const temporalAnnotations = collabStore.annotations.filter((a) => a.type === "TEMPORAL" && a.timestamp_sec !== undefined);

    // Synthetic playhead timer when no external video stream URL is active
    useEffect(() => {
      if (!isSyntheticMode || !isPlaying) return;
      const interval = setInterval(() => {
        setCurrentTime((prev) => {
          const next = prev >= duration ? 0 : prev + 0.25;
          if (onTimeUpdate) onTimeUpdate(next);
          return next;
        });
      }, 250);
      return () => clearInterval(interval);
    }, [isSyntheticMode, isPlaying, duration, onTimeUpdate]);

    // HLS initialization & lifecycle
    useEffect(() => {
      if (!src) {
        setIsSyntheticMode(true);
        return;
      }

      setIsSyntheticMode(false);
      const video = videoRef.current;
      if (!video) return;

      if (src.includes(".m3u8") && Hls.isSupported()) {
        const hls = new Hls({
          enableWorker: true,
          lowLatencyMode: true,
        });
        hlsRef.current = hls;

        hls.loadSource(src);
        hls.attachMedia(video);

        hls.on(Hls.Events.MANIFEST_PARSED, () => {
          setHasError(false);
        });

        hls.on(Hls.Events.ERROR, (_, data) => {
          if (data.fatal) {
            switch (data.type) {
              case Hls.ErrorTypes.NETWORK_ERROR:
                hls.startLoad();
                break;
              case Hls.ErrorTypes.MEDIA_ERROR:
                hls.recoverMediaError();
                break;
              default:
                hls.destroy();
                setHasError(true);
                setIsSyntheticMode(true);
                break;
            }
          }
        });

        return () => {
          hls.destroy();
          hlsRef.current = null;
        };
      } else if (video.canPlayType("application/vnd.apple.mpegurl") || src.endsWith(".mp4")) {
        video.src = src;
        video.addEventListener("error", () => {
          setHasError(true);
          setIsSyntheticMode(true);
        });
      }
    }, [src]);

    // Imperative seeking and control handles
    const seekTo = useCallback(
      (seconds: number) => {
        const clamped = Math.max(0, Math.min(seconds, duration));
        setCurrentTime(clamped);
        if (videoRef.current && !isSyntheticMode) {
          videoRef.current.currentTime = clamped;
        }
        if (onTimeUpdate) onTimeUpdate(clamped);
        if (onSeek) onSeek(clamped);
      },
      [duration, isSyntheticMode, onTimeUpdate, onSeek]
    );

    const play = useCallback(() => {
      setIsPlaying(true);
      if (videoRef.current && !isSyntheticMode) {
        videoRef.current.play().catch(() => {});
      }
    }, [isSyntheticMode]);

    const pause = useCallback(() => {
      setIsPlaying(false);
      if (videoRef.current && !isSyntheticMode) {
        videoRef.current.pause();
      }
    }, [isSyntheticMode]);

    useImperativeHandle(
      ref,
      () => ({
        seekTo,
        play,
        pause,
        getCurrentTime: () => currentTime,
      }),
      [seekTo, play, pause, currentTime]
    );

    const handleVideoTimeUpdate = () => {
      if (videoRef.current && !isSyntheticMode) {
        const t = videoRef.current.currentTime;
        setCurrentTime(t);
        if (onTimeUpdate) onTimeUpdate(t);
      }
    };

    const handleLoadedMetadata = () => {
      if (videoRef.current && !isNaN(videoRef.current.duration)) {
        setDuration(videoRef.current.duration);
      }
    };

    const togglePlay = () => {
      if (isPlaying) {
        pause();
      } else {
        play();
      }
    };

    const cyclePlaybackRate = () => {
      const rates = [0.5, 1, 2];
      const next = rates[(rates.indexOf(playbackRate) + 1) % rates.length];
      setPlaybackRate(next);
      if (videoRef.current) {
        videoRef.current.playbackRate = next;
      }
    };

    const toggleFullscreen = () => {
      if (!containerRef.current) return;
      if (document.fullscreenElement) {
        document.exitFullscreen();
      } else {
        containerRef.current.requestFullscreen();
      }
    };

    const handleDropFlag = () => {
      // In a real app, prompt for text or open side thread
      const text = window.prompt("Enter flag description:", "Review this frame.");
      if (text) {
        collabStore.addAnnotation({
          id: `ann-tp-${Date.now()}`,
          type: "TEMPORAL",
          timestamp_sec: currentTime,
          author: {
            id: "u-me",
            name: "You",
            role: "Operator",
            avatarColor: "bg-cyan-500",
            status: "online",
          },
          text,
          mentions: [],
          created_at: Date.now(),
        });
      }
    };

    // Calculate current frame index for precision HUD
    const currentFrame = Math.floor(currentTime * fps);

    return (
      <div
        ref={containerRef}
        className={cn(
          "relative aspect-video w-full rounded-lg border border-scada-border bg-black overflow-hidden flex flex-col justify-between select-none group",
          className
        )}
      >
        {/* Top HUD Overlay */}
        <div className="z-20 flex items-center justify-between p-3 bg-gradient-to-b from-black/80 to-transparent">
          <div className="flex items-center gap-2">
            <span className="badge-red flex items-center gap-1 text-[10px]">
              <span
                className={cn(
                  "h-1.5 w-1.5 rounded-full bg-red-500",
                  isPlaying && "animate-pulse"
                )}
              />
              {streamName}
            </span>
            <span className="badge-cyan text-[10px]">FPS: {fps}</span>
            {isSyntheticMode && (
              <span className="badge-cyan text-[9px] font-mono font-bold">
                [SYNTHETIC PLAYHEAD]
              </span>
            )}
          </div>

          <div className="flex items-center gap-2 font-mono text-[11px] text-scada-muted bg-slate-900/80 px-2 py-0.5 rounded border border-scada-border">
            <span>FRAME:</span>
            <strong className="text-white">{currentFrame.toString().padStart(5, "0")}</strong>
          </div>
        </div>

        {/* Center Video Canvas / Synthetic Rail View */}
        <div className="relative flex-1 flex items-center justify-center overflow-hidden">
          {src && !hasError ? (
            <video
              ref={videoRef}
              className="h-full w-full object-contain"
              onTimeUpdate={handleVideoTimeUpdate}
              onLoadedMetadata={handleLoadedMetadata}
              onPlay={() => setIsPlaying(true)}
              onPause={() => setIsPlaying(false)}
              playsInline
              muted={isMuted}
            />
          ) : (
            /* Control Room Synthetic Optical Track Stream */
            <div className="absolute inset-0 scada-grid flex items-center justify-center">
              <svg viewBox="0 0 600 340" className="w-full h-full opacity-60">
                {/* Rails Perspective */}
                <line x1="160" y1="340" x2="260" y2="120" stroke="#38BDF8" strokeWidth="4" />
                <line x1="440" y1="340" x2="340" y2="120" stroke="#38BDF8" strokeWidth="4" />
                {/* Sleepers */}
                {[0.2, 0.4, 0.6, 0.8].map((ratio, i) => {
                  const y = 120 + ratio * 220;
                  const x1 = 260 - ratio * 100;
                  const x2 = 340 + ratio * 100;
                  return (
                    <line
                      key={i}
                      x1={x1}
                      y1={y}
                      x2={x2}
                      y2={y}
                      stroke="#475569"
                      strokeWidth="7"
                    />
                  );
                })}
              </svg>

              {/* Crosshair Center Reticle */}
              <div className="pointer-events-none absolute inset-0 flex items-center justify-center opacity-40">
                <div className="h-10 w-px bg-cyan-400" />
                <div className="absolute h-px w-10 bg-cyan-400" />
                <div className="absolute h-6 w-6 rounded-full border border-cyan-400/50" />
              </div>
            </div>
          )}

          {/* AI Bounding Box Overlay */}
          {defects && defects.length > 0 && (
            <BoundingBoxOverlay defects={defects} currentTimeSec={currentTime} />
          )}
        </div>

        {/* Bottom Custom SCADA Controls Bar */}
        <div className="z-20 flex flex-col gap-1.5 p-3 bg-slate-950/90 border-t border-scada-border backdrop-blur">
          {/* Scrubber Timeline Bar */}
          <div className="relative flex items-center group/scrubber h-4">
            <input
              type="range"
              min="0"
              max={duration || 60}
              step="0.1"
              value={currentTime}
              onChange={(e) => seekTo(parseFloat(e.target.value))}
              className="absolute inset-0 w-full h-1.5 self-center bg-slate-800 rounded-lg appearance-none cursor-pointer accent-scada-accent transition-all z-10 hover:h-2"
            />
            {/* Render Temporal Annotations */}
            {temporalAnnotations.map((ann) => {
              if (ann.timestamp_sec === undefined || !duration) return null;
              const pct = (ann.timestamp_sec / duration) * 100;
              return (
                <div
                  key={ann.id}
                  className="absolute top-0 z-20 cursor-pointer group/flag -ml-1.5"
                  style={{ left: `${pct}%` }}
                  onClick={() => seekTo(ann.timestamp_sec!)}
                  title={`${ann.author.name}: ${ann.text}`}
                >
                  <div className={`w-0 h-0 border-l-[6px] border-l-transparent border-r-[6px] border-r-transparent border-b-[8px] ${ann.author.avatarColor.replace('bg-', 'border-b-')} shadow-lg drop-shadow-md transition-transform transform group-hover/flag:scale-150`} />
                </div>
              );
            })}
          </div>

          {/* Controls Cluster */}
          <div className="flex items-center justify-between font-mono text-xs">
            <div className="flex items-center gap-2">
              {/* Play / Pause */}
              <button
                onClick={togglePlay}
                className="flex h-7 w-7 items-center justify-center rounded bg-scada-accent/20 border border-scada-accent text-scada-accent hover:bg-scada-accent/30 transition"
                title={isPlaying ? "Pause Video" : "Play Video"}
              >
                {isPlaying ? <Pause size={14} /> : <Play size={14} className="ml-0.5" />}
              </button>

              {/* Step Back / Step Forward */}
              <button
                onClick={() => seekTo(currentTime - 1)}
                className="flex h-7 w-7 items-center justify-center rounded bg-slate-800 text-slate-300 hover:bg-slate-700 transition"
                title="Step -1s"
              >
                <Rewind size={13} />
              </button>

              <button
                onClick={() => seekTo(currentTime + 1)}
                className="flex h-7 w-7 items-center justify-center rounded bg-slate-800 text-slate-300 hover:bg-slate-700 transition"
                title="Step +1s"
              >
                <FastForward size={13} />
              </button>

              {/* Time display: HH:mm:ss / HH:mm:ss */}
              <div className="flex items-center gap-1 text-[11px] text-white ml-2 font-bold">
                <span className="text-cyan-400">{formatDuration(Math.floor(currentTime))}</span>
                <span className="text-scada-muted">/</span>
                <span className="text-slate-400">{formatDuration(Math.floor(duration))}</span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {/* Drop Flag */}
              <button
                onClick={handleDropFlag}
                className="flex items-center gap-1 px-2 py-1 mr-1 rounded bg-slate-800 text-slate-300 hover:bg-scada-accent/20 hover:text-scada-accent transition text-[10px] font-bold border border-transparent hover:border-scada-accent/50"
                title="Drop Temporal Flag"
              >
                <Flag size={12} />
                <span className="hidden sm:inline">FLAG</span>
              </button>

              {/* Speed multiplier toggle */}
              <button
                onClick={cyclePlaybackRate}
                className="px-2 py-1 rounded bg-slate-800 text-slate-300 hover:bg-slate-700 text-[10px] font-bold"
                title="Playback Speed"
              >
                {playbackRate}x
              </button>

              {/* Mute toggle */}
              <button
                onClick={() => setIsMuted(!isMuted)}
                className="p-1 rounded text-slate-400 hover:text-white transition"
                title={isMuted ? "Unmute" : "Mute"}
              >
                {isMuted ? <VolumeX size={15} /> : <Volume2 size={15} />}
              </button>

              {/* Fullscreen */}
              <button
                onClick={toggleFullscreen}
                className="p-1 rounded text-slate-400 hover:text-white transition"
                title="Toggle Fullscreen"
              >
                <Maximize size={15} />
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }
);
