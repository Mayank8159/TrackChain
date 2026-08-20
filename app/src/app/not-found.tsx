// 404 page for unknown routes.

import Link from "next/link";
import { Button } from "@/components/ui/Button";

export default function NotFound() {
  return (
    <div className="flex min-h-[70vh] flex-col items-center justify-center gap-4 bg-scada-bg p-6 text-scada-text text-center font-mono">
      <div className="text-6xl font-bold text-scada-cyan/40">404</div>
      <h2 className="text-sm font-bold uppercase tracking-widest text-scada-text">
        Track Segment Not Found
      </h2>
      <p className="max-w-md text-xs text-scada-muted">
        The requested monitoring route or telemetry identifier does not exist in the active rail topology.
      </p>
      <div className="mt-4">
        <Link href="/">
          <Button variant="primary" size="sm">
            Return to Control Room
          </Button>
        </Link>
      </div>
    </div>
  );
}
