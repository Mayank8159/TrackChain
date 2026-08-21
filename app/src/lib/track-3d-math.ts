import * as THREE from "three";
import type { TelemetryPoint } from "./types";

/**
 * Maps a TQI (Track Quality Index) score (0–100) to an RGB color gradient.
 * 85–100: Pristine Emerald Green [0.05, 0.95, 0.55]
 * 65–84:  Good Cyan/Blue [0.15, 0.75, 0.95]
 * 45–64:  Moderate Amber [0.95, 0.75, 0.15]
 * 0–44:   Severe Degradation Crimson [0.95, 0.20, 0.25]
 */
export function tqiToColor(tqiScore: number = 85): [number, number, number] {
  const score = Math.max(0, Math.min(100, tqiScore));
  if (score >= 85) {
    return [0.05, 0.92, 0.55]; // Neon Emerald
  } else if (score >= 65) {
    return [0.15, 0.75, 0.95]; // Cyber Cyan
  } else if (score >= 45) {
    return [0.95, 0.72, 0.15]; // Glowing Amber
  } else {
    return [0.95, 0.22, 0.25]; // Crimson Red
  }
}

export interface Projected3DTrack {
  leftRailVertices: Float32Array;
  rightRailVertices: Float32Array;
  centerVertices: Float32Array;
  sleeperMatrices: THREE.Matrix4[];
  vertexColors: Float32Array;
  minZ: number;
  maxZ: number;
  lengthMeters: number;
  pointCount: number;
}

export interface ProjectionOptions {
  cantExaggeration?: number;
  gaugeExaggeration?: number;
  alignmentExaggeration?: number;
  nominalGaugeM?: number;
}

/**
 * Projects a 1D EN 13848 telemetry array into 3D Cartesian coordinates.
 * Z-axis: Chainage in meters (forward).
 * X-axis: Lateral alignment deviation + gauge offset.
 * Y-axis: Cross-level (cant) rotation + vertical unevenness.
 */
export function projectTelemetryTo3D(
  telemetry: TelemetryPoint[],
  options: ProjectionOptions = {}
): Projected3DTrack {
  const {
    cantExaggeration = 2.5,
    gaugeExaggeration = 2.0,
    alignmentExaggeration = 2.0,
    nominalGaugeM = 1.676, // Broad gauge (Indian Railways standard)
  } = options;

  if (!telemetry || telemetry.length === 0) {
    return {
      leftRailVertices: new Float32Array(0),
      rightRailVertices: new Float32Array(0),
      centerVertices: new Float32Array(0),
      sleeperMatrices: [],
      vertexColors: new Float32Array(0),
      minZ: 0,
      maxZ: 0,
      lengthMeters: 0,
      pointCount: 0,
    };
  }

  const n = telemetry.length;
  const leftRailVertices = new Float32Array(n * 3);
  const rightRailVertices = new Float32Array(n * 3);
  const centerVertices = new Float32Array(n * 3);
  const vertexColors = new Float32Array(n * 3);
  const sleeperMatrices: THREE.Matrix4[] = [];

  let minZ = Infinity;
  let maxZ = -Infinity;

  for (let i = 0; i < n; i++) {
    const pt = telemetry[i];

    // Chainage Z-coordinate
    const chainageM = (pt as any).chainageM ?? (pt as any).chainage_m ?? i * 5;
    const z = chainageM;
    if (z < minZ) minZ = z;
    if (z > maxZ) maxZ = z;

    // Track Geometry parameters with fallbacks
    const rawGaugeMm = (pt as any).trackGaugeMm ?? (pt as any).gauge_mm ?? 1676;
    const gaugeDeviationM = ((rawGaugeMm - 1676) / 1000) * gaugeExaggeration;
    const actualGaugeM = nominalGaugeM + gaugeDeviationM;

    const rawCantMm = (pt as any).cantMm ?? (pt as any).cant_mm ?? 0;
    const cantRad = ((rawCantMm / 1000) / nominalGaugeM) * cantExaggeration;

    const rawAlignMm = (pt as any).alignmentDevMm ?? (pt as any).alignment_mm ?? 0;
    const alignM = (rawAlignMm / 1000) * alignmentExaggeration;

    const rawVertMm = (pt as any).verticalUnevennessMm ?? (pt as any).vert_unevenness_mm ?? 0;
    const vertM = rawVertMm / 1000;

    // Half gauge offset in X
    const halfGauge = actualGaugeM / 2;

    // Centerline position
    const centerX = alignM;
    const centerY = vertM;
    centerVertices[i * 3] = centerX;
    centerVertices[i * 3 + 1] = centerY;
    centerVertices[i * 3 + 2] = z;

    // Left Rail (X = -halfGauge, Y elevated by cant)
    const leftX = centerX - halfGauge * Math.cos(cantRad);
    const leftY = centerY + halfGauge * Math.sin(cantRad);
    leftRailVertices[i * 3] = leftX;
    leftRailVertices[i * 3 + 1] = leftY;
    leftRailVertices[i * 3 + 2] = z;

    // Right Rail (X = +halfGauge, Y depressed by cant)
    const rightX = centerX + halfGauge * Math.cos(cantRad);
    const rightY = centerY - halfGauge * Math.sin(cantRad);
    rightRailVertices[i * 3] = rightX;
    rightRailVertices[i * 3 + 1] = rightY;
    rightRailVertices[i * 3 + 2] = z;

    // Sleeper matrix: positioned at center, rotated by cant angle
    const sleeperMatrix = new THREE.Matrix4();
    const position = new THREE.Vector3(centerX, centerY - 0.08, z);
    const rotation = new THREE.Quaternion().setFromEuler(
      new THREE.Euler(0, 0, -cantRad, "XYZ")
    );
    const scale = new THREE.Vector3(actualGaugeM * 1.5, 1, 1);
    sleeperMatrix.compose(position, rotation, scale);
    sleeperMatrices.push(sleeperMatrix);

    // Calculate TQI score (100 - weighted deviations)
    const vibration = (pt as any).vibrationRms ?? (pt as any).vibration_rms ?? 1.2;
    const twist = Math.abs((pt as any).twistMmPerM ?? (pt as any).twist_mm_per_m ?? 0);
    const tqi = Math.max(
      20,
      Math.min(100, 100 - vibration * 12 - twist * 8 - Math.abs(rawCantMm) * 0.15)
    );

    const [r, g, b] = tqiToColor(tqi);
    vertexColors[i * 3] = r;
    vertexColors[i * 3 + 1] = g;
    vertexColors[i * 3 + 2] = b;
  }

  return {
    leftRailVertices,
    rightRailVertices,
    centerVertices,
    sleeperMatrices,
    vertexColors,
    minZ: minZ === Infinity ? 0 : minZ,
    maxZ: maxZ === -Infinity ? 0 : maxZ,
    lengthMeters: maxZ - minZ,
    pointCount: n,
  };
}
