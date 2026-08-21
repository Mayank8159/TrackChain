// Fetch one session by ID gated by DEMO vs REAL mode (tc.v1).

import { api } from "../lib/api";
import type { MonitoringSession } from "../lib/types";
import { MOCK_SESSIONS } from "../lib/mock-provider";
import { useRoutedData } from "../lib/data-router";

export function useSession(sessionId: string) {
  const fallbackSession: MonitoringSession = MOCK_SESSIONS.find((s) => s.id === sessionId) || {
    id: sessionId,
    name: `NDLS-AGC Mainline Inspection Run (${sessionId})`,
    trackId: "IR-NR-01",
    trackSection: "New Delhi to Mathura Junction (Km 0.0 to 140.0)",
    startTime: "2026-08-21T06:00:00.000Z",
    status: "active",
    totalDistanceKm: 140.0,
    defectsCount: 5,
    operatorName: "Chief Track Inspector A. Sharma",
    weather: "Clear / 28°C",
  };

  return useRoutedData<MonitoringSession>({
    queryKey: ["session", sessionId],
    demoData: fallbackSession,
    fetchReal: () => api.getSessionById(sessionId),
    enabled: !!sessionId,
  });
}
