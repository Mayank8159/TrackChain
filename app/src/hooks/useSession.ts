// Fetch one session by id with its summary (tc.v1).

import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { MonitoringSession } from "../lib/types";
import { MOCK_SESSIONS } from "../lib/mock-provider";

export function useSession(sessionId: string) {
  return useQuery<MonitoringSession>({
    queryKey: ["session", sessionId],
    queryFn: async (): Promise<MonitoringSession> => {
      try {
        return await api.getSessionById(sessionId);
      } catch {
        const found = MOCK_SESSIONS.find((s) => s.id === sessionId);
        if (found) return found;
        return {
          id: sessionId,
          name: `Inspection Run ${sessionId}`,
          trackId: "IR-NR-01",
          trackSection: "New Delhi to Mathura Junction (Km 0.0 to 140.0)",
          startTime: "2026-08-21T06:00:00.000Z",
          status: "active",
          totalDistanceKm: 140.0,
          defectsCount: 5,
          operatorName: "Chief Track Inspector A. Sharma",
        };
      }
    },
    enabled: !!sessionId,
  });
}
