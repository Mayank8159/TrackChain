// Sortable/paginated table of defect events.

"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "../ui/Table";
import { SeverityBadge } from "./SeverityBadge";
import { formatChainage, formatTimestamp, formatConfidence } from "../../lib/format";
import type { DefectEvent } from "../../lib/types";

interface DefectTableProps {
  defects: DefectEvent[];
  selectedId?: string;
  onSelect?: (defect: DefectEvent) => void;
  onViewEvidence?: (defect: DefectEvent) => void;
}

export function DefectTable({
  defects,
  selectedId,
  onSelect,
  onViewEvidence,
}: DefectTableProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Event ID / Timestamp</TableHead>
          <TableHead>Chainage</TableHead>
          <TableHead>Defect Classification</TableHead>
          <TableHead>Severity</TableHead>
          <TableHead>Confidence</TableHead>
          <TableHead>Stream Source</TableHead>
          <TableHead className="text-right">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {defects.length === 0 ? (
          <TableRow>
            <TableCell colSpan={7} className="py-8 text-center text-scada-muted">
              No defect records matching current filters
            </TableCell>
          </TableRow>
        ) : (
          defects.map((d) => {
            const isSelected = selectedId === d.id;
            return (
              <TableRow
                key={d.id}
                onClick={() => onSelect?.(d)}
                className={`cursor-pointer ${
                  isSelected ? "bg-scada-cyan/10 border-l-2 border-scada-cyan" : ""
                }`}
              >
                <TableCell>
                  <div className="font-bold text-scada-text">{d.id}</div>
                  <div className="text-[10px] text-scada-muted">
                    {formatTimestamp(d.timestamp)}
                  </div>
                </TableCell>
                <TableCell className="font-semibold text-scada-cyan">
                  {formatChainage(d.chainageM)}
                </TableCell>
                <TableCell className="uppercase font-semibold">
                  {d.defectClass.replace("_", " ")}
                </TableCell>
                <TableCell>
                  <SeverityBadge severity={d.severity} />
                </TableCell>
                <TableCell className="font-mono text-scada-green">
                  {formatConfidence(d.confidence)}
                </TableCell>
                <TableCell>
                  <span className="badge-cyan uppercase">{d.streamSource}</span>
                </TableCell>
                <TableCell className="text-right space-x-2">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onViewEvidence?.(d);
                    }}
                    className="text-[11px] text-scada-cyan hover:underline"
                  >
                    Evidence
                  </button>
                  <Link
                    href={`/video?seek=${d.videoTimestampSec || 0}`}
                    className="text-[11px] text-scada-muted hover:text-scada-text hover:underline"
                    onClick={(e) => e.stopPropagation()}
                  >
                    Video →
                  </Link>
                </TableCell>
              </TableRow>
            );
          })
        )}
      </TableBody>
    </Table>
  );
}
