// Fetch and manage edge inspection units with deterministic fallback (tc.v1).

import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { Device } from "../lib/types";
import { MOCK_DEVICES } from "../lib/mock-provider";

export function useDevices() {
  return useQuery<Device[]>({
    queryKey: ["devices"],
    queryFn: async (): Promise<Device[]> => {
      try {
        const devices = await api.getDevices();
        return devices && devices.length > 0 ? devices : MOCK_DEVICES;
      } catch {
        return MOCK_DEVICES;
      }
    },
    initialData: MOCK_DEVICES,
  });
}
