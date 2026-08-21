// Centralized Chainage <-> Time <-> GPS Coordinate conversion and interpolation engine (tc.v1).

export interface Waypoint {
  name: string;
  code: string;
  km: number;
  chainageM: number;
  lat: number;
  lng: number;
}

export const DELHI_AGRA_WAYPOINTS: Waypoint[] = [
  { name: "New Delhi", code: "NDLS", km: 0, chainageM: 0, lat: 28.6427, lng: 77.2195 },
  { name: "Hazrat Nizamuddin", code: "NZM", km: 7.2, chainageM: 7200, lat: 28.5882, lng: 77.2534 },
  { name: "Faridabad", code: "FDB", km: 28.5, chainageM: 28500, lat: 28.4089, lng: 77.3178 },
  { name: "Palwal", code: "PWL", km: 58.0, chainageM: 58000, lat: 28.1436, lng: 77.3328 },
  { name: "Kosi Kalan", code: "KSV", km: 99.0, chainageM: 99000, lat: 27.7942, lng: 77.4325 },
  { name: "Mathura Jn", code: "MTJ", km: 134.0, chainageM: 134000, lat: 27.4924, lng: 77.6737 },
  { name: "Agra Cantt", code: "AGC", km: 140.0, chainageM: 140000, lat: 27.1583, lng: 78.0081 },
];

/**
 * Converts chainage in meters to video playback time in seconds
 * @param chainageM Current chainage position in meters
 * @param totalDistanceM Total corridor or session distance in meters (defaults to 25,000m for standard run)
 * @param totalDurationSec Total video duration in seconds (defaults to 60s)
 */
export function chainageToTime(
  chainageM: number,
  totalDistanceM = 25000,
  totalDurationSec = 60
): number {
  if (totalDistanceM <= 0) return 0;
  const ratio = Math.max(0, Math.min(1, chainageM / totalDistanceM));
  return Number((ratio * totalDurationSec).toFixed(2));
}

/**
 * Converts video playback time in seconds to chainage in meters
 * @param timeSec Current video playhead time in seconds
 * @param totalDurationSec Total video duration in seconds (defaults to 60s)
 * @param totalDistanceM Total corridor or session distance in meters (defaults to 25,000m)
 */
export function timeToChainage(
  timeSec: number,
  totalDurationSec = 60,
  totalDistanceM = 25000
): number {
  if (totalDurationSec <= 0) return 0;
  const ratio = Math.max(0, Math.min(1, timeSec / totalDurationSec));
  return Math.round(ratio * totalDistanceM);
}

/**
 * Interpolates GPS coordinates [lat, lng] along the corridor for any given chainage in meters
 * @param chainageM Chainage along the track in meters
 */
export function chainageToCoordinate(chainageM: number): [number, number] {
  const waypoints = DELHI_AGRA_WAYPOINTS;
  const maxChainage = waypoints[waypoints.length - 1].chainageM;
  const clamped = Math.max(0, Math.min(chainageM, maxChainage));

  // Find the two surrounding waypoints
  for (let i = 0; i < waypoints.length - 1; i++) {
    const p1 = waypoints[i];
    const p2 = waypoints[i + 1];

    if (clamped >= p1.chainageM && clamped <= p2.chainageM) {
      const segmentSpan = p2.chainageM - p1.chainageM;
      const progress = segmentSpan > 0 ? (clamped - p1.chainageM) / segmentSpan : 0;
      const lat = p1.lat + progress * (p2.lat - p1.lat);
      const lng = p1.lng + progress * (p2.lng - p1.lng);
      return [Number(lat.toFixed(6)), Number(lng.toFixed(6))];
    }
  }

  const last = waypoints[waypoints.length - 1];
  return [last.lat, last.lng];
}

/**
 * Formats chainage in meters to standardized Indian Railways chainage string: e.g. "Km 3+420"
 */
export function formatChainage(meters?: number | null): string {
  if (meters === undefined || meters === null || isNaN(meters)) return "Km 0+000";
  const km = Math.floor(meters / 1000);
  const m = Math.floor(Math.abs(meters % 1000));
  return `Km ${km}+${m.toString().padStart(3, "0")}`;
}
