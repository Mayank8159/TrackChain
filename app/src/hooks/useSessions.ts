// Fetch and cache the list of sessions with deterministic fallback (tc.v1).

import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { MonitoringSession } from "../lib/types";
import { MOCK_SESSIONS } from "../lib/mock-provider";

export function useSessions() {
  return useQuery<MonitoringSession[]>({
    queryKey: ["sessions"],
    queryFn: async () => {
      try {
        const res = await api.getSessions();
        return res && res.length > 0 ? res : MOCK_SESSIONS;
      } catch {
        return MOCK_SESSIONS;
      }
    },
    initialData: MOCK_SESSIONS,
  });
}
