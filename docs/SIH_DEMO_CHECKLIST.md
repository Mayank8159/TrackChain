# TrackChain — SIH Pre-Flight & Live Demonstration Checklist

This checklist guarantees a zero-failure, high-impact demonstration during the Smart India Hackathon jury evaluations.

---

## 1. Pre-Flight Hardware & Display Setup

* [ ] **Display Resolution & Scaling**: Set primary monitor resolution to 1920x1080 (100% zoom). Avoid arbitrary display scaling that clips SCADA charts.
* [ ] **Browser Cleanliness**: 
  * Open clean Google Chrome profile (disable all ad-blockers and third-party extensions).
  * Hide bookmarks bar (`Cmd+Shift+B` on Mac / `Ctrl+Shift+B` on Windows).
  * Enter Fullscreen mode (`Cmd+Shift+F` on Mac / `F11` on Windows).
* [ ] **Dual Monitor Workflow**:
  * **Screen 1 (Projector/Screen Share)**: TrackChain Web Dashboard (`http://localhost:3000`).
  * **Screen 2 (Presenter Notes)**: `docs/SIH_DEMO_SCRIPT.md` and `docs/SIH_QA_DEFENSE.md`.
* [ ] **Audio Unlock**: 
  * Ensure browser audio permission is allowed.
  * In `/alerts`, verify the "Audio Alarm Synthesizer" toggle is switched **ON** to enable live critical siren generation via the Web Audio API.

---

## 2. Technical Stack Readiness & Live Ingestion Proof

* [ ] **Production Next.js Frontend**:
  * Running locally on port 3000 via `pnpm run dev` or `pnpm start`.
  * Verify 11/11 routes are compiled and cached.
* [ ] **FastAPI Real-Time Streaming Daemon**:
  * Background backend running on `http://localhost:8000`.
  * Open Chrome DevTools $\rightarrow$ **Network Tab** $\rightarrow$ Filter by `Fetch/XHR` or `SSE`.
  * Keep this tab ready to prove to judges that alerts and telemetry are streamed over real SSE connections (`/api/alerts/stream`), not hardcoded in static arrays.
* [ ] **Fallback Redundancy Plan**:
  * If WiFi drops during the pitch, the system automatically falls back to `mock-provider.ts` and offline local storage caching with zero UI degradation. The Header LED will smoothly display `DEMO MODE` without throwing console errors.

---

## 3. Seed State Verification

* [ ] **Header Indicators**:
  * Wordmark: `TRACKCHAIN AI · Northern Railway ITMS`.
  * IST Clock: Ticking live in Indian Standard Time (`Asia/Kolkata`).
  * Connection Status LED: `LIVE SSE` (Green pulsing).
  * Alert Bell: Shows pending unacknowledged alerts count.
* [ ] **Route Line Diagram**:
  * 140.0 km corridor rendered between `NDLS` and `AGC`.
  * Color-coded pins aligned to exact Indian Railways chainage (`Km 3+420`, `Km 7+850`, `Km 12+100`, `Km 16+750`, `Km 21+950`).
* [ ] **Inspection Run**:
  * Session `ses-delhi-agra-001` pre-seeded with 60s HLS video stream, multi-waveform geometry waveforms, and bounding box annotations.
* [ ] **Instant Climax Shortcut**:
  * Pressing `Ctrl+Shift+D` or clicking `[⚡ Simulate Fault]` on `/` immediately injects a Critical IAL Twist Exceedance alert into the live stream.
