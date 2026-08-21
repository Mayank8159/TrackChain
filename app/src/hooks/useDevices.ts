// Fetch and manage edge inspection units gated by DEMO vs REAL mode (tc.v1).

import { api } from "../lib/api";
import type { Device } from "../lib/types";
import { MOCK_DEVICES } from "../lib/mock-provider";
import { useRoutedData } from "../lib/data-router";

export function useDevices() {
  return useRoutedData<Device[]>({
    queryKey: ["devices"],
    demoData: MOCK_DEVICES,
    fetchReal: () => api.getDevices(),
    staleTime: 30000,
  });
}
