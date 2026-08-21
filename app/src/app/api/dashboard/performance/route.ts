// Next.js Route Handler for /api/dashboard/performance (tc.v1).

import { NextResponse } from "next/server";
import { MOCK_PERFORMANCE_METRICS } from "@/lib/mock-provider";

export async function GET() {
  return NextResponse.json(MOCK_PERFORMANCE_METRICS, { status: 200 });
}
