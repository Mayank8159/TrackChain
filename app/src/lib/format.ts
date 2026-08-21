// Formatters: chainage (km/m), timestamps, durations, confidence.

export { formatChainage, chainageToTime, timeToChainage, chainageToCoordinate } from "./chainage";


export function formatChainageKm(chainageM: number, decimals = 3): string {
  return `${(chainageM / 1000).toFixed(decimals)} km`;
}

export function formatTimestamp(isoString: string): string {
  try {
    const d = new Date(isoString);
    return d.toLocaleString("en-IN", {
      dateStyle: "short",
      timeStyle: "medium",
      hour12: false,
    });
  } catch {
    return isoString;
  }
}

export function formatTimeOnly(isoString: string): string {
  try {
    const d = new Date(isoString);
    return d.toLocaleTimeString("en-IN", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
  } catch {
    return isoString;
  }
}

export function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  if (hours > 0) {
    return `${hours.toString().padStart(2, "0")}:${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  }
  return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
}

export function formatSessionDuration(startTime: string, endTime?: string): string {
  try {
    const start = new Date(startTime).getTime();
    const end = endTime ? new Date(endTime).getTime() : Date.now();
    const diffSec = Math.max(0, Math.floor((end - start) / 1000));
    return formatDuration(diffSec);
  } catch {
    return "00:00:00";
  }
}

export function formatRelativeTime(isoString: string): string {
  try {
    const elapsedSec = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000);
    if (elapsedSec < 30) return "Just now";
    if (elapsedSec < 60) return `${elapsedSec}s ago`;
    const mins = Math.floor(elapsedSec / 60);
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  } catch {
    return "Recent";
  }
}

export function formatConfidence(ratio: number): string {
  return `${(ratio * 100).toFixed(1)}%`;
}

