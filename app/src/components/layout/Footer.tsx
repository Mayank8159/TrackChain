// Footer with version, connection status, and links.

import React from "react";
import { ConnectionStatus } from "../live/ConnectionStatus";

export function Footer() {
  return (
    <footer className="flex flex-wrap items-center justify-between gap-4 border-t border-scada-border bg-scada-panel px-4 py-2.5 text-[10px] font-mono text-scada-muted lg:px-6">
      <div className="flex items-center gap-4">
        <span>
          SYSTEM: <strong className="text-scada-text">TrackChain AI Core</strong>
        </span>
        <span>
          STANDARDS: <strong className="text-scada-cyan">EN 13848-1</strong> /{" "}
          <strong className="text-scada-amber">RDSO CTI</strong>
        </span>
      </div>

      <div className="flex items-center gap-4">
        <ConnectionStatus />
        <span>
          BUILD: <strong className="text-scada-text">2026.08-PROD</strong>
        </span>
      </div>
    </footer>
  );
}
