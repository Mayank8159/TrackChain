// Fetch and subscribe to real-time Server-Sent Events (SSE) alerts with audio cues and triage actions (tc.v1).

import { useState, useEffect, useCallback } from "react";
import type { AlertEvent } from "../lib/types";
import { sseClient } from "../lib/sse";
import { MOCK_ALERTS } from "../lib/mock-provider";
import { audioManager } from "../lib/audio";

export function useAlerts() {
  const [alerts, setAlerts] = useState<AlertEvent[]>(MOCK_ALERTS);
  const [snoozedClasses, setSnoozedClasses] = useState<string[]>([]);
  const [soundEnabled, setSoundEnabled] = useState<boolean>(audioManager.isEnabled());

  const toggleSound = useCallback(() => {
    const next = !audioManager.isEnabled();
    audioManager.setEnabled(next);
    setSoundEnabled(next);
    if (next) {
      audioManager.playAckChime();
    }
  }, []);

  useEffect(() => {
    // Subscribe to live SSE alerts from backend /api/alerts/stream
    const unsubscribe = sseClient.subscribeAlerts((incomingAlert: any) => {
      if (!incomingAlert) return;
      const defectClass = incomingAlert.defect_class || incomingAlert.defectClass || "visual_anomaly";

      // Ignore if class is currently snoozed
      if (snoozedClasses.includes(defectClass)) return;

      const severity = incomingAlert.severity || "high";
      const newAlert: AlertEvent = {
        id: incomingAlert.id || `ALT-${Date.now()}`,
        defectId: incomingAlert.defect_id || incomingAlert.defectId || "DEF-001",
        severity,
        defectClass,
        chainageM: incomingAlert.chainage_m ?? incomingAlert.chainageM ?? 0,
        message:
          incomingAlert.message ||
          `Critical safety fault [${defectClass.toUpperCase()}] detected at ${(
            (incomingAlert.chainage_m || 0) / 1000
          ).toFixed(3)} km`,
        timestamp: incomingAlert.timestamp || new Date().toISOString(),
        acknowledged: false,
      };

      // Trigger audio alarm if sound is enabled
      if (severity === "critical") {
        audioManager.playCriticalAlarm();
      } else if (severity === "high") {
        audioManager.playHighWarning();
      }

      setAlerts((prev) => [newAlert, ...prev.filter((a) => a.id !== newAlert.id)]);
    });

    return () => {
      unsubscribe();
    };
  }, [snoozedClasses]);

  const acknowledgeAlert = useCallback((id: string, operator = "Chief Track Inspector") => {
    audioManager.playAckChime();
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

  const escalateAlert = useCallback((id: string) => {
    audioManager.playHighWarning();
    setAlerts((prev) =>
      prev.map((a) =>
        a.id === id
          ? {
              ...a,
              message: `[ESCALATED TO SUPERVISOR] ${a.message}`,
            }
          : a
      )
    );
  }, []);

  const muteClass = useCallback((defectClass: string) => {
    setSnoozedClasses((prev) => [...prev, defectClass]);
  }, []);

  return {
    alerts,
    acknowledgeAlert,
    escalateAlert,
    muteClass,
    snoozedClasses,
    soundEnabled,
    toggleSound,
  };
}
