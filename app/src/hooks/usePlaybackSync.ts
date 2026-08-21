// Bi-directional synchronization engine between video playhead and telemetry waveforms (tc.v1).

import { useState, useCallback, useMemo, RefObject } from "react";
import type { TelemetryPoint } from "../lib/types";
import type { VideoPlayerHandle } from "../components/video/VideoPlayer";

export interface PlaybackSyncOptions {
  telemetryData?: TelemetryPoint[];
  videoDurationSec?: number;
  videoRef?: RefObject<VideoPlayerHandle>;
}

export function usePlaybackSync({
  telemetryData = [],
  videoDurationSec = 60,
  videoRef,
}: PlaybackSyncOptions = {}) {
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [currentChainageM, setCurrentChainageM] = useState<number>(
    telemetryData[0]?.chainageM || 0
  );

  // Derive time-to-point and chainage-to-point lookup functions
  const { minChainage, maxChainage } = useMemo(() => {
    if (!telemetryData || telemetryData.length === 0) {
      return { minChainage: 0, maxChainage: 25000 };
    }
    const chainages = telemetryData.map((d) => d.chainageM);
    return {
      minChainage: Math.min(...chainages),
      maxChainage: Math.max(...chainages),
    };
  }, [telemetryData]);

  // Video -> Telemetry Sync
  const handleVideoTimeUpdate = useCallback(
    (timeSec: number) => {
      setCurrentTime(timeSec);

      if (!telemetryData || telemetryData.length === 0) return;

      // Find the telemetry point closest to this video timestamp ratio
      const ratio = Math.max(0, Math.min(1, timeSec / (videoDurationSec || 60)));
      const targetIndex = Math.min(
        telemetryData.length - 1,
        Math.floor(ratio * telemetryData.length)
      );

      const pt = telemetryData[targetIndex];
      if (pt) {
        setCurrentChainageM(pt.chainageM);
      }
    },
    [telemetryData, videoDurationSec]
  );

  // Telemetry Chart -> Video Sync
  const seekToChainage = useCallback(
    (chainageM: number) => {
      setCurrentChainageM(chainageM);

      if (!telemetryData || telemetryData.length === 0) return;

      // Find index of telemetry point closest to this chainage
      let closestIdx = 0;
      let minDiff = Infinity;

      for (let i = 0; i < telemetryData.length; i++) {
        const diff = Math.abs(telemetryData[i].chainageM - chainageM);
        if (diff < minDiff) {
          minDiff = diff;
          closestIdx = i;
        }
      }

      const ratio = closestIdx / Math.max(1, telemetryData.length - 1);
      const derivedTime = ratio * (videoDurationSec || 60);

      setCurrentTime(derivedTime);
      if (videoRef?.current) {
        videoRef.current.seekTo(derivedTime);
      }
    },
    [telemetryData, videoDurationSec, videoRef]
  );

  // Direct Time Seeking (e.g. from defect button click)
  const seekToTime = useCallback(
    (timeSec: number) => {
      setCurrentTime(timeSec);
      if (videoRef?.current) {
        videoRef.current.seekTo(timeSec);
      }

      if (!telemetryData || telemetryData.length === 0) return;

      const ratio = Math.max(0, Math.min(1, timeSec / (videoDurationSec || 60)));
      const targetIndex = Math.min(
        telemetryData.length - 1,
        Math.floor(ratio * telemetryData.length)
      );

      const pt = telemetryData[targetIndex];
      if (pt) {
        setCurrentChainageM(pt.chainageM);
      }
    },
    [telemetryData, videoDurationSec, videoRef]
  );

  return {
    currentTime,
    currentChainageM,
    minChainage,
    maxChainage,
    handleVideoTimeUpdate,
    seekToChainage,
    seekToTime,
  };
}
