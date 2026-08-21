// Next.js Route Handler for Server-Sent Events /api/alerts/stream (tc.v1).

export const dynamic = "force-dynamic";

export async function GET() {
  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    start(controller) {
      // Send initial keepalive ping
      controller.enqueue(encoder.encode(": ping - connected to trackchain sse channel\n\n"));

      // Periodic keepalive every 15s
      const interval = setInterval(() => {
        try {
          controller.enqueue(encoder.encode(": ping - keepalive\n\n"));
        } catch {
          clearInterval(interval);
        }
      }, 15000);

      // Clean up when stream is cancelled
      return () => {
        clearInterval(interval);
      };
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
