// Next.js Route Handler for /api/sessions probe & proxy (tc.v1).

import { NextResponse } from "next/server";
import { MOCK_SESSIONS } from "@/lib/mock-provider";

export async function GET() {
  return NextResponse.json(MOCK_SESSIONS, { status: 200 });
}
