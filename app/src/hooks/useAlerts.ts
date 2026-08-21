// Fetch and subscribe to real-time alerts gated by DEMO (Scripted Simulator) vs REAL (SSE Stream) (tc.v1).

import { useState, useEffect, useCallback } from "react";
import type { AlertEvent } from "../lib/types";
import { sseClient } from "../lib/sse";
import { MOCK_ALERTS } from "../lib/mock-provider";
import { audioManager } from "../lib/audio";
import { useModeStore } from "../stores/mode-store";
import { createDemoSSESimulator } from "../lib/sse-simulator";

export function useAlerts() {
  const { mode, setConnectionState } = useModeStore();
  const [alerts, setAlerts] = useState<AlertEvent[]>(MOCK_ALERTS);
  const [snoozedClasses, setSnoozedClasses] = useState<string[]>([]);
  const [soundEnabled, setSoundEnabled] = useState<boolean>(audioManager.isEnabled());

  const isDemo = mode === "DEMO";

  const toggleSound = useCallback(() => {
    const next = !audioManager.isEnabled();
    audioManager.setEnabled(next);
    setSoundEnabled(next);
    if (next) {
      audioManager.playAckChime();
    }
  }, []);

  const handleIncomingAlert = useCallback(
    (incomingAlert: any) => {
      if (!incomingAlert) return;
      const defectClass =
        incomingAlert.defect_class || incomingAlert.defectClass || "visual_anomaly";

      // Ignore if class is currently snoozed
      if (snoozedClasses.includes(defectClass)) return;

      const severity = incomingAlert.severity || "high";
      const chainage = incomingAlert.chainage_m ?? incomingAlert.chainageM ?? 0;
      const deterministicId =
        incomingAlert.id ||
        incomingAlert.defect_id ||
        incomingAlert.defectId ||
        `ALT-${chainage}-${defectClass}`;

      const newAlert: AlertEvent = {
        id: deterministicId,
        defectId: incomingAlert.defect_id || incomingAlert.defectId || deterministicId,
        severity,
        defectClass,
        chainageM: chainage,
        message:
          incomingAlert.message ||
          `Critical safety fault [${defectClass.toUpperCase()}] detected at ${(
            chainage / 1000
          ).toFixed(3)} km`,
        timestamp: incomingAlert.timestamp || new Date().toISOString(),
        acknowledged: false,
      };

      setAlerts((prev) => {
        if (
          prev.some(
            (a) =>
              a.id === newAlert.id ||
              (a.defectId === newAlert.defectId && a.chainageM === newAlert.chainageM)
          )
        ) {
          return prev;
        }

        // Trigger audio alarm if sound is enabled only on fresh alert encounter
        if (severity === "critical") {
          audioManager.playCriticalAlarm();
        } else if (severity === "high") {
          audioManager.playHighWarning();
        }

        return [newAlert, ...prev].slice(0, 50);
      });
    },
    [snoozedClasses]
  );

  // Alert ingestion stream lifecycle
  useEffect(() => {
    if (isDemo) {
      // 1. DEMO Mode: Run scripted deterministic simulator
      setConnectionState("ACTIVE");
      const sim = createDemoSSESimulator((demoAlert) => {
        handleIncomingAlert(demoAlert);
      });

      // Also listen to any manual trigger demo alert events broadcast via sseClient
      const unsubscribe = sseClient.subscribeAlerts((manualAlert: any) => {
        handleIncomingAlert(manualAlert);
      });

      return () => {
        sim.stop();
        unsubscribe();
      };
    }

    // 2. REAL Mode: Subscribe to live FastAPI SSE Stream
    const unsubscribeStatus = sseClient.subscribeStatus((status) => {
      if (status === "connected") {
        setConnectionState("ACTIVE");
      } else if (status === "connecting") {
        setConnectionState("DEGRADED");
      } else {
        setConnectionState("ERROR");
      }
    });

    const unsubscribeAlerts = sseClient.subscribeAlerts((liveAlert) => {
      handleIncomingAlert(liveAlert);
    });

    return () => {
      unsubscribeStatus();
      unsubscribeAlerts();
    };
  }, [isDemo, handleIncomingAlert, setConnectionState]);

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
    isDemo,
  };
}
