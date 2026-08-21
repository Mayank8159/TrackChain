// RDSO Track Geometry Limits — Dynamic threshold engine for Oracle module (tc.oracle.v1).
// Source: RDSO specification C-7012 (Track geometry parameters for safety)
// These limits govern when the Oracle declares a "predicted breach".

export type TrackClass = "CLASS_A" | "CLASS_B" | "CLASS_C";

export interface RDSOLimit {
  label: string;
  description: string;
  speed_kmh: number;
  tqi_critical: number;  // TQI score at which EMERGENCY action is required
  tqi_warning: number;   // TQI score at which CAUTION order is issued
  color: string;         // Threshold line color for chart
}

export const RDSO_LIMITS: Record<TrackClass, RDSOLimit> = {
  CLASS_A: {
    label: "Class A — High Speed Passenger",
    description: "Rajdhani / Shatabdi / Vande Bharat corridors (>= 130 km/h)",
    speed_kmh: 130,
    tqi_critical: 75,
    tqi_warning: 82,
    color: "#EF4444",
  },
  CLASS_B: {
    label: "Class B — Mixed Traffic",
    description: "Mail / Express / intercity corridors (80–110 km/h)",
    speed_kmh: 110,
    tqi_critical: 65,
    tqi_warning: 74,
    color: "#F97316",
  },
  CLASS_C: {
    label: "Class C — Heavy Freight",
    description: "DFC / freight loops (up to 80 km/h, high axle load)",
    speed_kmh: 80,
    tqi_critical: 50,
    tqi_warning: 60,
    color: "#F59E0B",
  },
};

export const DEFAULT_TRACK_CLASS: TrackClass = "CLASS_B";
