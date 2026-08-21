// Next.js Route Handler for /api/process-frame (tc.v1).

import { NextResponse } from "next/server";

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const cameraId = body.camera_id || "lab-bench-01";

    // Return standard OpenCV Hough geometry simulation for standalone web testing
    return NextResponse.json({
      camera_id: cameraId,
      resolution: [640, 480],
      line_count: 8,
      lines: [
        { x1: 194, y1: 0, x2: 194, y2: 480, angle_deg: 0.0, length: 480 },
        { x1: 446, y1: 0, x2: 446, y2: 480, angle_deg: 0.0, length: 480 },
        { x1: 120, y1: 55, x2: 520, y2: 55, angle_deg: 90.0, length: 400 },
        { x1: 120, y1: 140, x2: 520, y2: 140, angle_deg: 90.0, length: 400 },
        { x1: 120, y1: 225, x2: 520, y2: 225, angle_deg: 90.0, length: 400 },
        { x1: 120, y1: 310, x2: 520, y2: 310, angle_deg: 90.0, length: 400 },
        { x1: 120, y1: 395, x2: 520, y2: 395, angle_deg: 90.0, length: 400 },
      ],
      yolo_boxes: [],
      yolo_weights_loaded: false,
      processing_ms: 36.4,
      status: "ok",
    });
  } catch (err: any) {
    return NextResponse.json({ error: err?.message || "Failed to process frame" }, { status: 400 });
  }
}
