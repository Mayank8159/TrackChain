// Hook to fetch/poll telemetry series for a session.

import { useState, useEffect, useCallback } from "react";
import { api } from "../lib/api";
import type { TelemetryPoint } from "../lib/types";

export function useTelemetry(sessionId?: string, pollIntervalMs = 2000) {
  const [data, setData] = useState<TelemetryPoint[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTelemetry = useCallback(async () => {
    if (!sessionId) {
      setLoading(false);
      return;
    }
    try {
      const result = await api.getTelemetrySeries(sessionId);
      setData(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch telemetry");
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    fetchTelemetry();
    if (!pollIntervalMs || !sessionId) return;

    const interval = setInterval(fetchTelemetry, pollIntervalMs);
    return () => clearInterval(interval);
  }, [fetchTelemetry, pollIntervalMs, sessionId]);

  return { data, loading, error, refetch: fetchTelemetry };
}
