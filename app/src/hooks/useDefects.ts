// Hook to fetch defect events with filters, falling back to deterministic mock provider (tc.v1).

import { useState, useEffect, useCallback } from "react";
import { api } from "../lib/api";
import type { DefectEvent } from "../lib/types";
import { MOCK_DEFECTS } from "../lib/mock-provider";

interface DefectFilters {
  sessionId?: string;
  severity?: string;
  defectClass?: string;
}

export function useDefects(filters?: DefectFilters, pollIntervalMs = 0) {
  const [defects, setDefects] = useState<DefectEvent[]>(() => {
    return filterMockDefects(filters);
  });
  const [loading, setLoading] = useState<boolean>(true);
  const [isDemoData, setIsDemoData] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  function filterMockDefects(f?: DefectFilters): DefectEvent[] {
    return MOCK_DEFECTS.filter((d) => {
      if (f?.sessionId && d.sessionId !== f.sessionId) return false;
      if (f?.severity && f.severity !== "all" && d.severity !== f.severity) return false;
      if (f?.defectClass && f.defectClass !== "all" && d.defectClass !== f.defectClass) return false;
      return true;
    });
  }

  const fetchDefects = useCallback(async () => {
    try {
      const result = await api.getDefects(filters);
      if (result && result.length > 0) {
        setDefects(result);
        setIsDemoData(false);
      } else {
        setDefects(filterMockDefects(filters));
        setIsDemoData(true);
      }
      setError(null);
    } catch {
      setDefects(filterMockDefects(filters));
      setIsDemoData(true);
      setError(null);
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

  return { defects, loading, error, isDemoData, refetch: fetchDefects };
}
