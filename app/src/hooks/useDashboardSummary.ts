// Fetch dashboard summary KPIs gated by DEMO vs REAL mode (tc.v1).

import { api } from "../lib/api";
import type { DashboardSummary } from "../lib/types";
import { MOCK_DASHBOARD_SUMMARY } from "../lib/mock-provider";
import { useRoutedData } from "../lib/data-router";

export function useDashboardSummary() {
  return useRoutedData<DashboardSummary>({
    queryKey: ["dashboard-summary"],
    demoData: MOCK_DASHBOARD_SUMMARY,
    fetchReal: () => api.getDashboardSummary(),
    staleTime: 15000,
  });
}
