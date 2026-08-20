// Hook to fetch/poll defect events with filters.

import { useState, useEffect, useCallback } from "react";
import { api } from "../lib/api";
import type { DefectEvent } from "../lib/types";

interface DefectFilters {
  sessionId?: string;
  severity?: string;
  defectClass?: string;
}

export function useDefects(filters?: DefectFilters, pollIntervalMs = 3000) {
  const [defects, setDefects] = useState<DefectEvent[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDefects = useCallback(async () => {
    try {
      const result = await api.getDefects(filters);
      setDefects(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch defects");
    } finally {
      setLoading(false);
    }
  }, [filters?.sessionId, filters?.severity, filters?.defectClass]);

  useEffect(() => {
    fetchDefects();
    if (!pollIntervalMs) return;

    const interval = setInterval(fetchDefects, pollIntervalMs);
    return () => clearInterval(interval);
  }, [fetchDefects, pollIntervalMs]);

  return { defects, loading, error, refetch: fetchDefects };
}
