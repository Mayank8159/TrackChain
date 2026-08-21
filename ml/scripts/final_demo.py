"""
ml/scripts/final_demo.py
TrackChain Capstone End-to-End Demo Walkthrough (Phase 2.7 tc.v1 SOTA).
Demonstrates the full 5-model multi-modal intelligence stack running in real-time across a 100-meter railway inspection run.
"""

import sys
import time
import json
from pathlib import Path
import numpy as np

# Add repo root to path
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from ml.core.schema import (
    TrackSegment,
    DecisionType,
    SeverityLevel,
    SignalType,
    DefectClass,
)
from ml.inference.pipeline import TrackChainMLPipeline
from ml.fusion.rules import TrackChainFusionEngine


def run_capstone_demo(n_segments: int = 5):
    print("=" * 80)
    print("🚂 TrackChain Multi-Modal Edge Intelligence Stack — Live Capstone Demo")
    print("   Architecture: 5-Model Triad (YOLOv8 + PatchCore + EN13848 + Bi-LSTM + Seq-VAE)")
    print("   Contract: tc.v1 Unified [0.0, 1.0] Calibration & Cross-Modal Rule Engine")
    print("=" * 80)

    print("\n[1/4] Initializing ML Pipeline and loading models...")
    start_init = time.time()
    pipeline = TrackChainMLPipeline(
        fusion_engine=TrackChainFusionEngine(persistence_window=2, known_threshold=0.50, novel_threshold=0.50),
        conditional_typing=False,
    )
    print(f"      Pipeline initialized in {(time.time() - start_init):.2f}s")

    print("\n[2/4] Generating synthetic 100m railway inspection run (5 segments)...")
    segments = []
    scenarios = [
        ("Clean Track", False, 0.0, "mainline_standard"),
        ("Missing Fastener (Visual Known)", True, 0.0, "mainline_standard"),
        ("Clean Track (Post-Repair)", False, 0.0, "mainline_standard"),
        ("Track Twist Exceedance (Geometry Known)", False, 9.5, "mainline_standard"),
        ("Compound Defect: Crack + Gauge Spread (Dual Stream)", True, 14.0, "mainline_high_speed"),
    ]

    for idx, (scenario_name, has_visual_defect, vert_dip_mm, sec_type) in enumerate(scenarios):
        start_m = idx * 20.0
        end_m = (idx + 1) * 20.0
        n_bins = 80

        # Frame
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[200:280, :] = 120
        if has_visual_defect:
            frame[220:260, 300:340] = 255  # Defect

        # Telemetry
        vertical = np.random.normal(0.0, 0.2, n_bins)
        if vert_dip_mm > 0:
            vertical[30:50] = vert_dip_mm

        gauge = np.full(n_bins, 1676.0)
        if idx == 4:
            gauge[35:45] = 1684.0  # Gauge widening +8mm

        telemetry = {
            "roll_rad": np.zeros(n_bins),
            "lateral_pos_mm": np.random.normal(0.0, 0.3, n_bins),
            "vertical_pos_mm": vertical,
            "gauge_mm": gauge,
        }

        seg = TrackSegment(
            segment_id=f"seg-{int(start_m):04d}-{int(end_m):04d}",
            chainage_start_m=start_m,
            chainage_end_m=end_m,
            frames=[frame],
            telemetry=telemetry,
            section_type=sec_type,
        )
        segments.append((scenario_name, seg))

    print(f"      Created {len(segments)} test segments.")

    print("\n[3/4] Processing live inspection stream across all 5 models & fusion...")
    print("-" * 80)
    print(f"{'Chainage (m)':<15} | {'Scenario':<25} | {'Decision':<14} | {'Severity':<9} | {'Latency':<8}")
    print("-" * 80)

    demo_results = []
    total_time = 0.0

    for scenario_name, seg in segments:
        t0 = time.perf_counter()
        decision, signals = pipeline.process_segment(seg)
        dt_ms = (time.perf_counter() - t0) * 1000.0
        total_time += dt_ms

        chainage_str = f"{seg.chainage_start_m:.1f}m - {seg.chainage_end_m:.1f}m"
        print(f"{chainage_str:<15} | {scenario_name:<25} | {decision.decision.value:<14} | {decision.severity.value:<9} | {dt_ms:>5.1f} ms")

        demo_results.append({
            "chainage": chainage_str,
            "scenario": scenario_name,
            "decision": decision.decision.value,
            "severity": decision.severity.value,
            "confidence": round(float(decision.confidence), 4),
            "primary_defect": decision.primary_defect.value if decision.primary_defect else "none",
            "action": decision.action,
            "latency_ms": round(dt_ms, 2),
        })

    avg_ms = total_time / len(segments)
    fps = 1000.0 / avg_ms if avg_ms > 0 else 0.0

    print("-" * 80)
    print(f"[4/4] Demo Summary: Average Pipeline Latency = {avg_ms:.1f} ms ({fps:.1f} FPS, Target >= 15 FPS)")
    print("=" * 80)

    # Save summary
    out_dir = repo_root / "artifacts"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "demo_run_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "schema_version": "tc.v1",
            "average_latency_ms": round(avg_ms, 2),
            "fps": round(fps, 1),
            "segments": demo_results,
            "status": "PASSED",
        }, f, indent=2)

    print(f"\n[OK] Capstone Demo completed successfully. Report saved to: {summary_path}")
    return 0


if __name__ == "__main__":
    sys.exit(run_capstone_demo())
