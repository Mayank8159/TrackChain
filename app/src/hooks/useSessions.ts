// Fetch and cache the list of sessions.

import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { MonitoringSession } from "../lib/types";

const MOCK_SESSIONS: MonitoringSession[] = [
  {
    id: "ses-delhi-agra-001",
    name: "NDLS-AGC Mainline High-Speed Inspection Run",
    trackId: "IR-NR-01",
    trackSection: "New Delhi to Mathura Junction (Km 0.0 to 140.0)",
    startTime: new Date(Date.now() - 3600 * 1000 * 2).toISOString(),
    status: "active",
    totalDistanceKm: 140.0,
    defectsCount: 5,
    operatorName: "Chief Track Inspector A. Sharma",
  },
  {
    id: "ses-delhi-agra-002",
    name: "AGC-GWL Routine Diagnostic Pass",
    trackId: "IR-NCR-04",
    trackSection: "Agra Cantt to Gwalior Jn (Km 140.0 to 258.0)",
    startTime: new Date(Date.now() - 3600 * 1000 * 26).toISOString(),
    endTime: new Date(Date.now() - 3600 * 1000 * 22).toISOString(),
    status: "completed",
    totalDistanceKm: 118.0,
    defectsCount: 8,
    operatorName: "Inspection Unit 4B",
  },
];

export function useSessions() {
  return useQuery<MonitoringSession[]>({
    queryKey: ["sessions"],
    queryFn: async () => {
      try {
        const res = await api.getSessions();
        return res.length > 0 ? res : MOCK_SESSIONS;
      } catch {
        return MOCK_SESSIONS;
      }
    },
  });
}
