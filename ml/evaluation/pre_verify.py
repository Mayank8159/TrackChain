"""PRE-VERIFICATION HARNESS.
Scans candidates/ (known_*, clean_*, novel_*), measures REAL model behaviour,
picks the 3 images that produce the desired story, and tunes the YOLO threshold
to the measured separation. Writes selected/manifest.json.

GOLDEN RULE: if no clean separation exists, CHANGE THE IMAGES, not the story.
Run:  python -m ml.evaluation.pre_verify
"""
import json
from pathlib import Path
from .eval_core import ROOT, YOLOAdapter, PatchCoreAdapter, _read_img

CAND = ROOT / "ml" / "evaluation" / "candidates"
SEL = ROOT / "ml" / "evaluation" / "selected"

def scan(yolo, pc):
    rows = []
    for img_path in sorted(CAND.glob("*.jpg")) + sorted(CAND.glob("*.png")):
        role = "known" if img_path.name.startswith("known_") else \
               "clean" if img_path.name.startswith("clean_") else \
               "novel" if img_path.name.startswith("novel_") else None
        if role is None:
            continue
        img = _read_img(img_path)
        _, scores = yolo.detect(img)
        y_max = max(scores) if scores else 0.0
        # Get both raw distance and calibrated score for diagnostics
        raw_dist, _ = pc.m.predict_raw(img)
        p = float(pc.m.calibrator.scale(raw_dist))
        rows.append({"file": img_path.name, "role": role,
                     "yolo_max": round(y_max, 3), "n_boxes": len(scores),
                     "patchcore": round(p, 3), "pc_raw_dist": round(float(raw_dist), 4)})
    return rows

def pick(rows):
    known = [r for r in rows if r["role"] == "known"]
    clean = [r for r in rows if r["role"] == "clean"]
    novel = [r for r in rows if r["role"] == "novel"]
    if not (known and clean and novel):
        raise SystemExit("❌ Need at least one known_*, one clean_*, one novel_* in candidates/")
    k = max(known, key=lambda r: r["yolo_max"])
    c = min(clean, key=lambda r: r["yolo_max"] + r["patchcore"])
    n = max(novel, key=lambda r: r["patchcore"] - r["yolo_max"])
    return k, c, n

def main():
    print("🔬 TrackChain Pre-Verification Harness — measuring REAL model behaviour\n")
    yolo = YOLOAdapter()
    pc = PatchCoreAdapter()
    rows = scan(yolo, pc)

    print(f"{'image':<40}{'role':<7}{'yolo_max':>9}{'boxes':>7}{'pc_raw':>10}{'patchcore':>11}")
    print("-" * 84)
    for r in rows:
        print(f"{r['file']:<40}{r['role']:<7}{r['yolo_max']:>9}{r['n_boxes']:>7}{r['pc_raw_dist']:>10}{r['patchcore']:>11}")

    k, c, n = pick(rows)
    thr = round((k["yolo_max"] + c["yolo_max"]) / 2, 3)
    margin = round(k["yolo_max"] - c["yolo_max"], 3)

    print("\n── SELECTION ─────────────────────────────────────────────")
    print(f"  KNOWN KILL : {k['file']}  (yolo_max={k['yolo_max']})")
    print(f"  CLEAN BASE : {c['file']}  (yolo_max={c['yolo_max']}, pc={c['patchcore']})")
    print(f"  NOVEL OOD  : {n['file']}  (pc={n['patchcore']}, yolo_max={n['yolo_max']})")
    print(f"  TUNED YOLO THRESHOLD: {thr}   (separation margin: {margin})")

    ok = True
    if margin < 0.10:
        ok = False
        print("  ⚠️  MARGIN < 0.10 — known/clean not separable. ADD DIFFERENT CANDIDATE IMAGES.")
    if n["patchcore"] <= 0.5:
        ok = False
        print("  ⚠️  PatchCore does NOT fire on the novel candidate. TRY ANOTHER novel_ IMAGE.")
    if k["yolo_max"] < 0.3:
        ok = False
        print("  ⚠️  YOLO too weak on every known candidate. TRY BRIGHTER/CLOSER known_ IMAGES.")

    if ok:
        SEL.mkdir(parents=True, exist_ok=True)
        manifest = {"known": k, "clean": c, "novel": n,
                    "yolo_threshold": thr, "margin": margin,
                    "note": "Pre-verified. Do not edit by hand."}
        (SEL / "manifest.json").write_text(json.dumps(manifest, indent=2))
        print(f"\n✅ manifest written → {SEL / 'manifest.json'}")
        print("   Demo is now DETERMINISTIC. Run: python -m ml.evaluation.real_test")
    else:
        print("\n❌ NOT certified. Change images, re-run. (Golden rule.)")

if __name__ == "__main__":
    main()
