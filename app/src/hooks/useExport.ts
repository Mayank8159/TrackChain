// Trigger CSV/PDF export of sessions/defects.

import { useState } from "react";
import { exportToCSV } from "../lib/export";
import type { DefectEvent, MonitoringSession } from "../lib/types";

export function useExport() {
  const [isExporting, setIsExporting] = useState(false);

  const exportDefectsCSV = (defects: DefectEvent[], filename = "defects_registry.csv") => {
    setIsExporting(true);
    try {
      const rows = defects.map((d) => ({
        id: d.id,
        sessionId: d.sessionId,
        chainage_km: (d.chainageM / 1000).toFixed(3),
        defect_class: d.defectClass,
        severity: d.severity,
        confidence_pct: (d.confidence * 100).toFixed(1),
        source: d.streamSource,
        timestamp: d.timestamp,
        status: d.status,
      }));
      exportToCSV(filename, rows);
    } finally {
      setIsExporting(false);
    }
  };

  const exportSessionsCSV = (sessions: MonitoringSession[], filename = "monitoring_sessions.csv") => {
    setIsExporting(true);
    try {
      const rows = sessions.map((s) => ({
        sessionId: s.id,
        name: s.name,
        trackId: s.trackId,
        section: s.trackSection,
        distance_km: s.totalDistanceKm,
        defects_count: s.defectsCount,
        startTime: s.startTime,
        status: s.status,
      }));
      exportToCSV(filename, rows);
    } finally {
      setIsExporting(false);
    }
  };

  return { isExporting, exportDefectsCSV, exportSessionsCSV };
}
