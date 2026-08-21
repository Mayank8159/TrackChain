// Frontend DTO types; mirrors packages/shared contracts (tc.v1).

export * from "@trackchain/shared";

import type {
  SeverityLevel,
  DefectClass,
} from "@trackchain/shared";

export interface AlertEvent {
  id: string;
  defectId: string;
  severity: SeverityLevel;
  defectClass: DefectClass;
  chainageM: number;
  message: string;
  timestamp: string;
  acknowledged: boolean;
  acknowledgedBy?: string;
  acknowledgedAt?: string;
}

export interface ReportConfig {
  sessionId: string;
  trackSection: string;
  dateRange: [string, string];
  format: "pdf" | "csv";
  includeVisualEvidence: boolean;
  complianceStandard: "EN 13848" | "RDSO CTI";
}

export interface FilterState {
  sessionId?: string;
  severity?: string;
  defectClass?: string;
  streamSource?: string;
  chainageMin?: number;
  chainageMax?: number;
  dateFrom?: string;
  dateTo?: string;
}

export interface RealtimePayload {
  type: "telemetry" | "defect" | "alert" | "status" | "device_discovered";
  data: any;
  timestamp: string;
}
