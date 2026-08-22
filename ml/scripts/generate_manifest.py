import os
import json
import hashlib
from pathlib import Path

def compute_file_sha256(filepath):
    p = Path(filepath)
    if not p.exists() or not p.is_file():
        return ""
    hasher = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def main():
    repo_root = Path(__file__).resolve().parent.parent.parent
    calib_dir = repo_root / "artifacts" / "calibration"
    chk_dir = repo_root / "artifacts" / "checkpoints"
    exports_dir = repo_root / "artifacts" / "exports"

    manifest = {
        "schema_version": "tc.v1",
        "revision": "latest",
        "models": {}
    }

    # YOLO
    yolo_calib_path = calib_dir / "yolo_temp.json"
    if yolo_calib_path.exists():
        with open(yolo_calib_path, "r") as f:
            yolo_calib = json.load(f)
        
        artifact_path = exports_dir / "yolov8n_rail_best.onnx"
        sha256 = compute_file_sha256(artifact_path)
        
        manifest["models"]["yolo_visual_detector"] = {
            "method": "temperature",
            "T": yolo_calib.get("temperature", 1.839),
            "threshold": yolo_calib.get("threshold", 0.50),
            "artifact": "yolov8n_rail_best.onnx",
            "sha256": sha256
        }

    # PatchCore
    patchcore_calib_path = calib_dir / "patchcore_calibration.json"
    if patchcore_calib_path.exists():
        with open(patchcore_calib_path, "r") as f:
            patchcore_calib = json.load(f)
            
        artifact_path = chk_dir / "vision" / "patchcore_memory_bank.npz"
        sha256 = compute_file_sha256(artifact_path)
        
        manifest["models"]["patchcore_visual_anomaly"] = {
            "method": "sigmoid_p99",
            "T": patchcore_calib.get("threshold_p99", 21.936),
            "k": patchcore_calib.get("steepness_k", 0.5),
            "threshold": patchcore_calib.get("threshold", 0.50),
            "artifact": "patchcore_memory_bank.npz",
            "sha256": sha256
        }

    # Physics
    manifest["models"]["physics_en13848"] = {
        "method": "exceedance",
        "threshold": 0.50,
        "artifact": None
    }

    # BiLSTM
    bilstm_calib_path = calib_dir / "bilstm_temp.json"
    if bilstm_calib_path.exists():
        with open(bilstm_calib_path, "r") as f:
            bilstm_calib = json.load(f)
            
        artifact_path = chk_dir / "geometry" / "bilstm_fault_typing_enhanced.pt"
        sha256 = compute_file_sha256(artifact_path)
        
        manifest["models"]["bilstm_geometry_typing"] = {
            "method": "vector_scaling",
            "T": bilstm_calib.get("bilstm_temperature", 1.500),
            "weights": bilstm_calib.get("weights", [6]),
            "biases": bilstm_calib.get("biases", [6]),
            "threshold": bilstm_calib.get("threshold", 0.60),
            "artifact": "bilstm_fault_typing_enhanced.pt",
            "sha256": sha256
        }

    # Sequence VAE
    vae_calib_path = calib_dir / "vae_calibration.json"
    if vae_calib_path.exists():
        with open(vae_calib_path, "r") as f:
            vae_calib = json.load(f)
            
        artifact_path = chk_dir / "geometry" / "sequence_vae_enhanced.pt"
        sha256 = compute_file_sha256(artifact_path)
        
        manifest["models"]["sequence_vae_geometry_novel"] = {
            "method": "evt_sigmoid",
            "T": vae_calib.get("threshold_evt", 1.707),
            "k": vae_calib.get("steepness_k", 2.0),
            "threshold": vae_calib.get("threshold", 0.50),
            "artifact": "sequence_vae_enhanced.pt",
            "sha256": sha256
        }

    manifest_path = calib_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    
    print(f"Generated unified calibration manifest at {manifest_path}")

if __name__ == "__main__":
    main()
