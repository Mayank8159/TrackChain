// Fetch and cache the list of sessions gated by DEMO vs REAL mode (tc.v1).

import { api } from "../lib/api";
import type { MonitoringSession } from "../lib/types";
import { MOCK_SESSIONS } from "../lib/mock-provider";
import { useRoutedData } from "../lib/data-router";

export function useSessions() {
  return useRoutedData<MonitoringSession[]>({
    queryKey: ["sessions"],
    demoData: MOCK_SESSIONS,
    fetchReal: () => api.getSessions(),
    staleTime: 30000,
  });
}
