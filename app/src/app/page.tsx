// Dashboard home: KPI cards, recent defects, and live status.

"use client";

import React from "react";
import { ControlRoom } from "@/components/ControlRoom";

export default function DashboardHome() {
  return (
    <main className="min-h-screen bg-scada-bg text-scada-text">
      <ControlRoom />
    </main>
  );
}
