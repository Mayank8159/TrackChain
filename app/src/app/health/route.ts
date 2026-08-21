// Next.js Route Handler for root /health probe (tc.v1).

import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json(
    {
      status: "ok",
      service: "trackchain-frontend",
      timestamp: new Date().toISOString(),
      version: "1.0.0",
    },
    { status: 200 }
  );
}
