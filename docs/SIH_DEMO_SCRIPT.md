# TrackChain — 5-Minute SIH Winning Pitch & Live Presenter Script

**Target Time**: 4 minutes 45 seconds (Leaving 15s buffer before the 5:00 buzzer).  
**Presenter Tone**: Confident, operational, technically grounded, mission-critical.

---

## ⏱️ Minute 0:00 – 1:00: The Hook & Domain Problem

**Presenter Action**: Start on `/` (Operational Dashboard) in fullscreen dark mode.

> *"Respected Judges, Indian Railways manages the 4th largest railway network in the world — over 68,000 route kilometers. Today, track safety inspection still largely relies on manual foot patrols walking the tracks with handheld gauges, or sporadic recording cars running once every few months.*
>
> *This creates two massive vulnerabilities: first, manual foot patrols are life-threatening and slow. Second, micro-geometry anomalies like dynamic track twist or rail-head fatigue cracks develop rapidly under high-tonnage freight traffic between inspection cycles.*
>
> *This is **TrackChain**: an autonomous, real-time Intelligent Track Monitoring System (ITMS) that bridges edge computing nodes mounted directly on revenue trains with a centralized SCADA Mission Control."*

---

## ⏱️ Minute 1:00 – 2:00: The Macro Fleet Overview

**Presenter Action**: Hover over KPI cards, scroll to the Route Line Diagram, then quickly toggle to `/devices`.

> *"What you see here on the screen is our live Operational Command Center. We are currently monitoring the high-speed corridor between New Delhi (`NDLS`) and Agra Cantt (`AGC`).*
>
> *Across the top, our KPI cluster gives the Chief Track Engineer immediate situational awareness: Active Runs, Track Quality Index (TQI Category A), and zero unacknowledged Immediate Action Limit (IAL) alarms.*
>
> *Below is our signature **Route Line Diagram**, rendering the physical 140-kilometer mainline with color-coded defect chainage markers. If we click over to **Edge Hardware**, you can see our distributed sensor fleet — Jetson vision nodes and Raspberry Pi IMU units streaming optics, 3-axis vibrations, and RTK GNSS telemetry at 100 Hz."*

---

## ⏱️ Minute 2:00 – 3:30: The Live Incident (THE CLIMAX)

**Presenter Action**: Return to `/`. Click `[⚡ Simulate Fault]` (or press `Ctrl+Shift+D`). The dual-tone Web Audio siren sounds, the red alert banner flashes in the Live Feed, and the Header badge pulses `[1]`. Click `[View in Session ▶]` on the alert.

> *(🚨 Audio Cue plays: Dual-tone SCADA emergency siren)*
>
> *"Right now, an edge node has detected a critical anomaly! Our EN 13848-1 physics engine just registered a **Track Twist Exceedance of 6.2 mm/m** on the Down Main line at Km 21+950.*
>
> *(Clicking View in Session)*
>
> *With a single click, we drill straight into the Inspection Viewer hero workspace. Notice what just happened: the system automatically synchronized our 4K optical footage with the high-frequency telemetry waveform at that exact millisecond.*
>
> *As we scrub through the playhead, the IMU vibration waveform, track gauge, and cant charts track in mathematical lockstep. Our YOLOv8 model has drawn a localized bounding box around the rail flaw, and the telemetry spikes confirm the physical dynamic impact on the bogie."*

---

## ⏱️ Minute 3:30 – 4:30: Human-in-the-Loop Triage & State Propagation

**Presenter Action**: Click `Inspect` on the defect list to open the slide-in `EvidenceDrawer`. Click `[Acknowledge]`. Then switch to `/map`.

> *"In railway safety, AI should advise, but human engineers must decide. We open our **AI Evidence Drawer**.*
>
> *Here, the engineer inspects the calibrated confidence score (94%), the raw sensor inputs, and the RDSO standard violation code. The inspector clicks **'Acknowledge'**.*
>
> *(Click Acknowledge — chime sounds and green toast appears)*
>
> *Instantly, this state change propagates across the entire network. If we jump to our **GIS Track Map**, the corridor is mapped with CartoDB Dark Matter tiles, color-coded by Track Quality Index, and the defect marker reflects the acknowledged status in real time for field maintenance crews."*

---

## ⏱️ Minute 4:30 – 5:00: Compliance Export & The Final Punchline

**Presenter Action**: Navigate to `/reports`. Select Session `ses-delhi-agra-001`. Click `[Generate & Export Report]`. Show the downloaded CSV.

> *"Finally, railway governance requires rigorous compliance. In our **Reports workspace**, an engineer selects the session and exports the complete inspection run into standardized **RDSO TMD v2.4 CSV and Apache Parquet formats** for downstream ingestion into the Indian Railways TMS (Track Management System).*
>
> *TrackChain replaces subjective, dangerous manual inspections with continuous, mathematically verified autonomous intelligence. We prevent derailments before they happen.*
>
> *Thank you, and we are ready for your technical questions."*
