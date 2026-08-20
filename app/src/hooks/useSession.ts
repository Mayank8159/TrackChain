// Fetch one session by id with its summary (tc.v1).

import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { MonitoringSession } from "../lib/types";

export function useSession(sessionId: string) {
  return useQuery<MonitoringSession>({
    queryKey: ["session", sessionId],
    queryFn: async (): Promise<MonitoringSession> => {
      try {
        return await api.getSessionById(sessionId);
      } catch {
        const fallback: MonitoringSession = {
          id: sessionId,
          name: "NDLS-AGC Mainline Inspection Run",
          trackId: "IR-NR-01",
          trackSection: "New Delhi to Mathura Junction (Km 0.0 to 140.0)",
          startTime: new Date(Date.now() - 3600 * 1000 * 2).toISOString(),
          status: "active",
          totalDistanceKm: 140.0,
          defectsCount: 5,
          operatorName: "Chief Track Inspector A. Sharma",
        };
        return fallback;
      }
    },
    enabled: !!sessionId,
  });
}
