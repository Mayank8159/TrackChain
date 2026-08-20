// Fetch and subscribe to alerts.

import { useState, useEffect, useCallback } from "react";
import type { AlertEvent } from "../lib/types";

const INITIAL_ALERTS: AlertEvent[] = [
  {
    id: "ALT-001",
    defectId: "DEF-001",
    severity: "critical",
    defectClass: "crack",
    chainageM: 3420,
    message: "Transverse railhead fracture detected with high confidence",
    timestamp: new Date().toISOString(),
    acknowledged: false,
  },
  {
    id: "ALT-002",
    defectId: "DEF-005",
    severity: "critical",
    defectClass: "twist_exceedance",
    chainageM: 21950,
    message: "EN 13848-1 Immediate Action Limit (IAL) twist exceeded (4.2 mm/m)",
    timestamp: new Date(Date.now() - 60000).toISOString(),
    acknowledged: false,
  },
  {
    id: "ALT-003",
    defectId: "DEF-002",
    severity: "high",
    defectClass: "gauge_widening",
    chainageM: 7850,
    message: "Track gauge widening: 1448mm (+13mm above 1435mm standard)",
    timestamp: new Date(Date.now() - 180000).toISOString(),
    acknowledged: true,
    acknowledgedBy: "Inspector Verma",
    acknowledgedAt: new Date(Date.now() - 120000).toISOString(),
  },
];

export function useAlerts() {
  const [alerts, setAlerts] = useState<AlertEvent[]>(INITIAL_ALERTS);

  const acknowledgeAlert = useCallback((id: string, operator = "Station Master") => {
    setAlerts((prev) =>
      prev.map((a) =>
        a.id === id
          ? {
              ...a,
              acknowledged: true,
              acknowledgedBy: operator,
              acknowledgedAt: new Date().toISOString(),
            }
          : a
      )
    );
  }, []);

  return { alerts, acknowledgeAlert };
}
