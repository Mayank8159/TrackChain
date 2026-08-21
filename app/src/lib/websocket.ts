// Deprecated websocket adapter: delegates to native Server-Sent Events (SSE) client (tc.v1).

import { sseClient, type ConnectionStatusType, type RealtimeListener, type StatusListener } from "./sse";
import type { RealtimePayload } from "./types";

export { sseClient as realtimeClient, type ConnectionStatusType, type RealtimeListener, type StatusListener };
