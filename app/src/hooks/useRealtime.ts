// Manage websocket/SSE connection; dispatch live telemetry/defect events.

import { useState, useEffect } from "react";
import { realtimeClient } from "../lib/websocket";
import type { RealtimePayload } from "../lib/types";

export function useRealtime() {
  const [lastPayload, setLastPayload] = useState<RealtimePayload | null>(null);
  const [status, setStatus] = useState<"connected" | "connecting" | "disconnected">(
    realtimeClient.getStatus()
  );

  useEffect(() => {
    const unsubData = realtimeClient.subscribe((payload) => {
      setLastPayload(payload);
    });

    const unsubStatus = realtimeClient.subscribeStatus((newStatus) => {
      setStatus(newStatus);
    });

    return () => {
      unsubData();
      unsubStatus();
    };
  }, []);

  return { lastPayload, status };
}
