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
  staleTime = 10000,
  enabled = true,
  refetchInterval,
}: RoutedDataOptions<T>): RoutedDataResult<T> {
  const { mode, setConnectionState } = useModeStore();
  const isDemo = mode === "DEMO";

  const resolvedDemoData = typeof demoData === "function" ? (demoData as () => T)() : demoData;

  const query = useQuery<T, Error>({
    queryKey: ["app_data", mode, ...queryKey],
    queryFn: fetchReal,
    enabled: enabled,
    staleTime,
    refetchInterval,
    retry: 1,
    retryDelay: 1000,
  });

  useEffect(() => {
    if (query.isError) {
      if (!isDemo) setConnectionState("ERROR");
    } else if (query.isSuccess) {
      setConnectionState("ACTIVE");
    }
  }, [isDemo, query.isError, query.isSuccess, setConnectionState]);

  const activeData = query.data !== undefined ? query.data : resolvedDemoData;

  return {
    data: activeData,
    isLoading: query.isLoading && activeData === undefined,
    isError: !isDemo && query.isError,
    error: query.error,
    isDemo,
    refetch: query.refetch,
  };
}

