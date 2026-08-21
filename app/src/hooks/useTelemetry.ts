// Hook to fetch/poll telemetry series for a session with deterministic mock fallback (tc.v1).

import { useState, useEffect, useCallback } from "react";
import { api } from "../lib/api";
import type { TelemetryPoint } from "../lib/types";
import { MOCK_TELEMETRY_SERIES } from "../lib/mock-provider";

export function useTelemetry(sessionId?: string, pollIntervalMs = 0) {
  const [data, setData] = useState<TelemetryPoint[]>(MOCK_TELEMETRY_SERIES);
  const [loading, setLoading] = useState<boolean>(true);
  const [isDemoData, setIsDemoData] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTelemetry = useCallback(async () => {
    if (!sessionId) {
      setData(MOCK_TELEMETRY_SERIES);
      setIsDemoData(true);
      setLoading(false);
      return;
    }
    try {
      const result = await api.getTelemetrySeries(sessionId);
      if (result && result.length > 0) {
        setData(result);
        setIsDemoData(false);
      } else {
        setData(MOCK_TELEMETRY_SERIES);
        setIsDemoData(true);
      }
      setError(null);
    } catch {
      setData(MOCK_TELEMETRY_SERIES);
      setIsDemoData(true);
      setError(null);
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

  return { data, loading, error, isDemoData, refetch: fetchTelemetry };
}
