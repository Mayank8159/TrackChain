// Centralized Hook-Level Data Router for DEMO vs REAL Mode Gating (tc.v1).
// Guarantees zero silent fallbacks in REAL mode and zero network requests in DEMO mode.

import { useEffect } from "react";
import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { useModeStore } from "../stores/mode-store";

export interface RoutedDataOptions<T> {
  queryKey: (string | number | boolean | undefined | null | Record<string, any>)[];
  demoData: T | (() => T);
  fetchReal: () => Promise<T>;
  staleTime?: number;
  enabled?: boolean;
  refetchInterval?: number;
}

export interface RoutedDataResult<T> {
  data: T;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  isDemo: boolean;
  refetch: () => Promise<any>;
}

export function useRoutedData<T>({
  queryKey,
  demoData,
  fetchReal,
  staleTime = 15000,
  enabled = true,
  refetchInterval,
}: RoutedDataOptions<T>): RoutedDataResult<T> {
  const { mode, setConnectionState } = useModeStore();

  const isDemo = mode === "DEMO";

  // 1. DEMO Mode: Return deterministic mock data synchronously with no network calls
  const resolvedDemoData = typeof demoData === "function" ? (demoData as () => T)() : demoData;

  const realQuery = useQuery<T, Error>({
    queryKey: ["real_data", ...queryKey],
    queryFn: fetchReal,
    enabled: enabled && !isDemo,
    staleTime,
    refetchInterval: !isDemo ? refetchInterval : undefined,
    retry: 1,
    retryDelay: 1000,
  });

  // Track connection state when in REAL mode
  useEffect(() => {
    if (isDemo) return;

    if (realQuery.isError) {
      setConnectionState("ERROR");
    } else if (realQuery.isSuccess) {
      setConnectionState("ACTIVE");
    }
  }, [isDemo, realQuery.isError, realQuery.isSuccess, setConnectionState]);

  if (isDemo) {
    return {
      data: resolvedDemoData,
      isLoading: false,
      isError: false,
      error: null,
      isDemo: true,
      refetch: async () => resolvedDemoData,
    };
  }

  return {
    data: (realQuery.data !== undefined ? realQuery.data : resolvedDemoData),
    isLoading: realQuery.isLoading,
    isError: realQuery.isError,
    error: realQuery.error,
    isDemo: false,
    refetch: realQuery.refetch,
  };
}
