// Centralized, deterministic mock data provider for TrackChain (tc.v1).
// Eradicates Math.random() in favor of seeded, verifiable railway telemetry & defect events.

import type {
  MonitoringSession,
  DefectEvent,
  TelemetryPoint,
  Device,
  DashboardSummary,
  AlertEvent,
  LineGeometry,
} from "./types";

// ============================================================================
// 1. Deterministic Monitoring Sessions
// ============================================================================

export const MOCK_SESSIONS: MonitoringSession[] = [
  {
    id: "ses-delhi-agra-001",
    name: "NDLS-AGC Mainline High-Speed Inspection Run",
    trackId: "IR-NR-01",
    trackSection: "New Delhi to Mathura Junction (Km 0.0 to 140.0)",
    startTime: "2026-08-21T06:00:00.000Z",
    status: "active",
    totalDistanceKm: 140.0,
    defectsCount: 5,
    operatorName: "Chief Track Inspector A. Sharma",
    weather: "Clear / 28°C",
  },
  {
    id: "ses-delhi-agra-002",
    name: "AGC-GWL Routine Diagnostic Pass",
    trackId: "IR-NCR-04",
    trackSection: "Agra Cantt to Gwalior Jn (Km 140.0 to 258.0)",
    startTime: "2026-08-20T14:30:00.000Z",
    endTime: "2026-08-20T18:45:00.000Z",
    status: "completed",
    totalDistanceKm: 118.0,
    defectsCount: 8,
    operatorName: "Inspection Unit 4B",
    weather: "Overcast",
  },
  {
    id: "ses-mumbai-surat-003",
    name: "BCT-ST Western Dedicated Freight Corridor Inspection",
    trackId: "IR-WR-DFC-02",
    trackSection: "Mumbai Central to Surat (Km 0.0 to 263.0)",
    startTime: "2026-08-19T08:15:00.000Z",
    endTime: "2026-08-19T13:30:00.000Z",
    status: "completed",
    totalDistanceKm: 263.0,
    defectsCount: 12,
    operatorName: "Senior Section Engineer R. K. Patel",
    weather: "Light Rain",
  },
];

// ============================================================================
// 2. Deterministic Defect Registry
// ============================================================================

export const MOCK_DEFECTS: DefectEvent[] = [
  {
    id: "DEF-001",
    sessionId: "ses-delhi-agra-001",
    timestamp: "2026-08-21T06:15:32.000Z",
    chainageM: 3420,
    defectClass: "crack",
    defectFamily: "visual_surface",
    severity: "critical",
    confidence: 0.94,
    sourceModel: "YOLOv8-Rail-Head-v2",
    modelVersion: "2.4.1",
    streamSource: "vision",
    videoTimestampSec: 14.5,
    description: "Transverse rail head crack on right rail running surface",
    status: "open",
    coordinates: { lat: 28.592, lng: 77.248 },
    latitude: 28.592,
    longitude: 77.248,
    supportingSignals: [
      {
        signalId: "sig-001",
        sessionId: "ses-delhi-agra-001",
        segmentId: "seg-01",
        modelName: "YOLOv8-Rail",
        modelVersion: "2.4.1",
        signalType: "visual_known",
        rawScore: 0.94,
        calibratedScore: 0.94,
        threshold: 0.7,
        fired: true,
        label: "crack",
        bbox: [55, 48, 72, 65], // [ymin, xmin, ymax, xmax] in %
        timestamp: "2026-08-21T06:15:32.000Z",
      },
    ],
  },
  {
    id: "DEF-002",
    sessionId: "ses-delhi-agra-001",
    timestamp: "2026-08-21T06:18:10.000Z",
    chainageM: 7850,
    defectClass: "gauge_widening",
    defectFamily: "geometry",
    severity: "high",
    confidence: 0.89,
    sourceModel: "EN13848-Physics-Engine",
    modelVersion: "1.2.0",
    streamSource: "geometry",
    videoTimestampSec: 26.0,
    description: "Track gauge measured at 1448mm (+13mm above 1435mm standard)",
    status: "open",
    coordinates: { lat: 28.561, lng: 77.265 },
    latitude: 28.561,
    longitude: 77.265,
    supportingSignals: [
      {
        signalId: "sig-002",
        sessionId: "ses-delhi-agra-001",
        segmentId: "seg-01",
        modelName: "Geometry-Gauge-Estimator",
        modelVersion: "1.2.0",
        signalType: "geometry_known",
        rawScore: 0.89,
        calibratedScore: 0.89,
        threshold: 0.75,
        fired: true,
        label: "gauge_widening",
        bbox: [42, 28, 68, 72],
        timestamp: "2026-08-21T06:18:10.000Z",
      },
    ],
  },
  {
    id: "DEF-003",
    sessionId: "ses-delhi-agra-001",
    timestamp: "2026-08-21T06:22:45.000Z",
    chainageM: 12100,
    defectClass: "missing_fastener",
    defectFamily: "visual_component",
    severity: "medium",
    confidence: 0.96,
    sourceModel: "YOLOv8-Fastener-v3",
    modelVersion: "3.1.0",
    streamSource: "vision",
    videoTimestampSec: 38.2,
    description: "Missing Pandrol clip fastener on sleeper #482",
    status: "acknowledged",
    acknowledgedBy: "Chief Track Inspector A. Sharma",
    acknowledgedAt: "2026-08-21T06:30:00.000Z",
    coordinates: { lat: 28.528, lng: 77.289 },
    latitude: 28.528,
    longitude: 77.289,
    supportingSignals: [
      {
        signalId: "sig-003",
        sessionId: "ses-delhi-agra-001",
        segmentId: "seg-02",
        modelName: "YOLOv8-Fastener",
        modelVersion: "3.1.0",
        signalType: "visual_known",
        rawScore: 0.96,
        calibratedScore: 0.96,
        threshold: 0.75,
        fired: true,
        label: "missing_fastener",
        bbox: [60, 32, 74, 44],
        timestamp: "2026-08-21T06:22:45.000Z",
      },
    ],
  },
  {
    id: "DEF-004",
    sessionId: "ses-delhi-agra-001",
    timestamp: "2026-08-21T06:26:12.000Z",
    chainageM: 16400,
    defectClass: "spalling",
    defectFamily: "visual_surface",
    severity: "high",
    confidence: 0.88,
    sourceModel: "Fused-Vision-Geometry",
    modelVersion: "2.0.0",
    streamSource: "fused",
    videoTimestampSec: 47.0,
    description: "Surface spalling with localized high-frequency vertical acceleration (2.8g RMS)",
    status: "open",
    coordinates: { lat: 28.495, lng: 77.302 },
    latitude: 28.495,
    longitude: 77.302,
    supportingSignals: [
      {
        signalId: "sig-004",
        sessionId: "ses-delhi-agra-001",
        segmentId: "seg-03",
        modelName: "Fused-Surface-Model",
        modelVersion: "2.0.0",
        signalType: "visual_known",
        rawScore: 0.88,
        calibratedScore: 0.88,
        threshold: 0.7,
        fired: true,
        label: "spalling",
        bbox: [50, 56, 66, 70],
        timestamp: "2026-08-21T06:26:12.000Z",
      },
    ],
  },
  {
    id: "DEF-005",
    sessionId: "ses-delhi-agra-001",
    timestamp: "2026-08-21T06:31:05.000Z",
    chainageM: 21950,
    defectClass: "twist_exceedance",
    defectFamily: "geometry",
    severity: "critical",
    confidence: 0.92,
    sourceModel: "EN13848-Physics-Engine",
    modelVersion: "1.2.0",
    streamSource: "geometry",
    videoTimestampSec: 54.5,
    description: "EN 13848-1 track twist rate exceeded: 4.2mm/m over 3m base",
    status: "open",
    coordinates: { lat: 28.452, lng: 77.319 },
    latitude: 28.452,
    longitude: 77.319,
    supportingSignals: [
      {
        signalId: "sig-005",
        sessionId: "ses-delhi-agra-001",
        segmentId: "seg-04",
        modelName: "Twist-Exceedance-Engine",
        modelVersion: "1.2.0",
        signalType: "geometry_known",
        rawScore: 0.92,
        calibratedScore: 0.92,
        threshold: 0.8,
        fired: true,
        label: "twist_exceedance",
        bbox: [38, 22, 75, 78],
        timestamp: "2026-08-21T06:31:05.000Z",
      },
    ],
  },
];

// ============================================================================
// 3. Deterministic Synced Telemetry Series (60 seconds, 1 Hz)
// ============================================================================

export function generateDeterministicTelemetrySeries(count = 60): TelemetryPoint[] {
  const points: TelemetryPoint[] = [];
  const baseTime = new Date("2026-08-21T06:00:00.000Z").getTime();

  for (let i = 0; i < count; i++) {
    const chainage = 12000 + i * 20; // 20 m/s = 72 km/h
    const isAnomalyZone = i >= 25 && i <= 30;
    const speedKmh = 72.0 + Math.sin(i * 0.1) * 2.0;

    points.push({
      id: `tel-point-${i}`,
      sessionId: "ses-delhi-agra-001",
      timestamp: new Date(baseTime + i * 1000).toISOString(),
      chainageM: chainage,
      speedMps: speedKmh / 3.6,
      speedKmh: Number(speedKmh.toFixed(1)),
      vibrationRms: isAnomalyZone ? 2.85 : Number((0.85 + Math.sin(i * 0.2) * 0.15).toFixed(2)),
      trackGaugeMm: isAnomalyZone ? 1448.0 : Number((1435.2 + Math.cos(i * 0.15) * 0.8).toFixed(1)),
      cantMm: Number((12.0 + Math.sin(i * 0.08) * 3.5).toFixed(1)),
      twistMmPerM: isAnomalyZone ? 3.85 : Number((1.1 + Math.sin(i * 0.25) * 0.3).toFixed(2)),
      verticalUnevennessMm: isAnomalyZone ? 5.2 : Number((1.2 + Math.cos(i * 0.3) * 0.2).toFixed(1)),
      alignmentDevMm: isAnomalyZone ? 7.4 : Number((1.8 + Math.sin(i * 0.18) * 0.3).toFixed(1)),
      latitude: 28.588 - (i * 0.001),
      longitude: 77.253 + (i * 0.0008),
    });
  }
  return points;
}

export const MOCK_TELEMETRY_SERIES = generateDeterministicTelemetrySeries(60);

// ============================================================================
// 4. Deterministic Registered Edge Devices
// ============================================================================

export const MOCK_DEVICES: Device[] = [
  {
    deviceId: "DEV-EDGE-01",
    deviceName: "Front Bogie Optical Scanner (Left Rail)",
    hardwareVersion: "Raspberry Pi 5 (8GB) + Sony IMX477",
    firmwareVersion: "v1.2.0-prod",
    cameraModel: "Sony IMX477 12.3MP HQ Camera",
    imuModel: "TDK InvenSense ICM-42688-P",
    gnssModel: "u-blox ZED-F9P RTK GNSS",
    status: "recording",
    batteryVoltageV: 12.4,
    cpuTempC: 44.5,
    lastSeenAt: "2026-08-21T06:35:10.000Z",
  },
  {
    deviceId: "DEV-EDGE-02",
    deviceName: "Under-Chassis IMU & Geometry Profiler",
    hardwareVersion: "Raspberry Pi 5 (4GB) + ADIS16488",
    firmwareVersion: "v1.2.0-prod",
    imuModel: "Analog Devices ADIS16488 iSensor MEMS",
    gnssModel: "u-blox ZED-F9P RTK GNSS",
    status: "online",
    batteryVoltageV: 12.6,
    cpuTempC: 42.1,
    lastSeenAt: "2026-08-21T06:35:12.000Z",
  },
  {
    deviceId: "DEV-EDGE-03",
    deviceName: "Rear Bogie Visual Anomaly Inspector",
    hardwareVersion: "NVIDIA Jetson Orin Nano (8GB) + Basler Ace 2",
    firmwareVersion: "v1.1.4-orin",
    cameraModel: "Basler Ace 2 5MP Global Shutter",
    status: "online",
    batteryVoltageV: 12.1,
    cpuTempC: 48.0,
    lastSeenAt: "2026-08-21T06:35:08.000Z",
  },
];

// ============================================================================
// 5. Deterministic Critical Alert Center Events
// ============================================================================

export const MOCK_ALERTS: AlertEvent[] = [
  {
    id: "ALT-001",
    defectId: "DEF-001",
    severity: "critical",
    defectClass: "crack",
    chainageM: 3420,
    message: "Transverse railhead fracture detected with high confidence (94%)",
    timestamp: "2026-08-21T06:15:32.000Z",
    acknowledged: false,
  },
  {
    id: "ALT-002",
    defectId: "DEF-005",
    severity: "critical",
    defectClass: "twist_exceedance",
    chainageM: 21950,
    message: "EN 13848-1 Immediate Action Limit (IAL) twist exceeded (4.2 mm/m)",
    timestamp: "2026-08-21T06:31:05.000Z",
    acknowledged: false,
  },
  {
    id: "ALT-003",
    defectId: "DEF-002",
    severity: "high",
    defectClass: "gauge_widening",
    chainageM: 7850,
    message: "Track gauge widening: 1448mm (+13mm above 1435mm standard)",
    timestamp: "2026-08-21T06:18:10.000Z",
    acknowledged: true,
    acknowledgedBy: "Inspector Verma",
    acknowledgedAt: "2026-08-21T06:25:00.000Z",
  },
];

// ============================================================================
// 6. SIH Live Demo Fault Injection Utility
// ============================================================================

export function triggerDemoAlert(): AlertEvent {
  const demoAlert: AlertEvent = {
    id: `ALT-LIVE-${Date.now().toString().slice(-4)}`,
    defectId: "DEF-005",
    severity: "critical",
    defectClass: "twist_exceedance",
    chainageM: 21950,
    message: "CRITICAL IAL ALARM: Track Twist Exceedance (6.2 mm/m over 3m base) detected on Down Main Line",
    timestamp: new Date().toISOString(),
    acknowledged: false,
  };
  return demoAlert;
}


// ============================================================================
// 6. Deterministic Dashboard Summary
// ============================================================================

export const MOCK_DASHBOARD_SUMMARY: DashboardSummary = {
  totalDefects: 5,
  criticalDefects: 2,
  distanceCoveredKm: 521.0,
  avgSpeedKmh: 105.4,
  openAlerts: 2,
  defectCountsByClass: {
    crack: 1,
    gauge_widening: 1,
    missing_fastener: 1,
    spalling: 1,
    twist_exceedance: 1,
  },
  severityDistribution: {
    critical: 2,
    high: 2,
    medium: 1,
    low: 0,
    normal: 0,
  },
};

// ============================================================================
// 7. Deterministic Canvas Frame & Line Geometries
// ============================================================================

export function getDeterministicLineGeometries(width = 640, height = 480): LineGeometry[] {
  const lines: LineGeometry[] = [
    // Left running rail
    { x1: 20, y1: 180, x2: width - 20, y2: 180, angle_deg: 0.0, length: width - 40 },
    // Right running rail
    { x1: 20, y1: 300, x2: width - 20, y2: 300, angle_deg: 0.0, length: width - 40 },
  ];

  // 9 evenly spaced concrete sleepers
  const sleeperCount = 9;
  for (let i = 0; i < sleeperCount; i++) {
    const x = 60 + (i * (width - 120)) / (sleeperCount - 1);
    lines.push({
      x1: x,
      y1: 190,
      x2: x,
      y2: 290,
      angle_deg: 90.0,
      length: 100.0,
    });
  }

  return lines;
}

export const MOCK_LINE_GEOMETRIES = getDeterministicLineGeometries(640, 480);
