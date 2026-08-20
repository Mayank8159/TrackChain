// Map marker colored by severity with popup summary.

"use client";

import React from "react";
import { SEVERITY_CONFIG } from "../../lib/constants";
import { formatChainage } from "../../lib/format";
import type { DefectEvent } from "../../lib/types";

interface DefectMarkerProps {
  defect: DefectEvent;
  isSelected?: boolean;
  onClick?: () => void;
}

export function DefectMarker({
  defect,
  isSelected,
  onClick,
}: DefectMarkerProps) {
  const config = SEVERITY_CONFIG[defect.severity] || SEVERITY_CONFIG.medium;

  return (
    <button
      onClick={onClick}
      className="group relative flex items-center justify-center p-1 transition-transform hover:scale-125 focus:outline-none"
      title={`${defect.defectClass} - ${formatChainage(defect.chainageM)}`}
    >
      <span
        className="absolute h-4 w-4 rounded-full opacity-40 animate-ping"
        style={{ backgroundColor: config.color }}
      />
      <span
        className={`relative h-3 w-3 rounded-full border border-scada-panel ${
          isSelected ? "ring-2 ring-white scale-125" : ""
        }`}
        style={{ backgroundColor: config.color }}
      />
    </button>
  );
}
