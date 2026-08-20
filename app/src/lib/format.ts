// Formatters: chainage (km/m), timestamps, durations, confidence.

export function formatChainage(chainageM: number): string {
  const km = Math.floor(chainageM / 1000);
  const m = Math.round(chainageM % 1000);
  return `Km ${km}+${m.toString().padStart(3, "0")}`;
}

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
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
}

export function formatConfidence(ratio: number): string {
  return `${(ratio * 100).toFixed(1)}%`;
}
