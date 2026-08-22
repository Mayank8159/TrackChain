import os
import json
import hashlib
from pathlib import Path
from src.services.s3 import get_s3_client
from src.config import get_settings

settings = get_settings()

MODEL_BUCKET = getattr(settings, "MODEL_BUCKET", "trackchain-models-prod")
LOCAL_MODEL_DIR = Path("/tmp/models")
LOCAL_MODEL_DIR.mkdir(parents=True, exist_ok=True)


def verify_sha256(file_path: Path, expected_hash: str) -> bool:
    with open(file_path, "rb") as f:
        actual_hash = hashlib.sha256(f.read()).hexdigest()
        return actual_hash == expected_hash


def load_artifacts() -> dict:
    """
    Downloads and verifies ONNX models, memory banks, and manifest.json 
    from the private AWS S3 bucket during backend startup.
    Falls back gracefully to local dummy structure during development or network isolation.
    """
    fallback_structure = {
        "calibration": {"method": "tc.v1"},
        "yolo_int8": "yolov8n_rail_best.onnx",
        "bilstm": "bilstm_fault_typing_enhanced.pt",
        "seqvae": "sequence_vae_enhanced.pt",
        "patchcore_bank": "patchcore_memory_bank.npz",
    }

    if os.getenv("SKIP_ARTIFACT_DOWNLOAD", "").lower() == "true":
        print("[Artifacts] SKIP_ARTIFACT_DOWNLOAD is active. Using fallback artifacts.")
        return fallback_structure

    try:
        s3 = get_s3_client()
        if not s3:
            print("[Artifacts] S3 client not available. Using fallback artifacts.")
            return fallback_structure

        print(f"[Artifacts] Loading model registry from s3://{MODEL_BUCKET}...")
        manifest_obj = s3.get_object(Bucket=MODEL_BUCKET, Key="manifest.json")
        manifest = json.loads(manifest_obj["Body"].read().decode("utf-8"))

        out = {"calibration": manifest.get("calibration", {"method": "tc.v1"})}

        for name, cfg in manifest.get("models", {}).items():
            if cfg.get("artifact"):
                artifact_key = cfg["artifact"]
                local_path = LOCAL_MODEL_DIR / artifact_key

                if not local_path.exists() or not verify_sha256(local_path, cfg["sha256"]):
                    print(f"[Artifacts] Downloading {artifact_key} to {local_path}...")
                    s3.download_file(MODEL_BUCKET, artifact_key, str(local_path))

                    if not verify_sha256(local_path, cfg["sha256"]):
                        raise RuntimeError(f"Security violation: {artifact_key} hash mismatch!")

                out[name] = str(local_path)

        return out
    except Exception as exc:
        print(f"[Artifacts] S3 model download skipped or failed ({exc}). Using fallback artifact structure.")
        return fallback_structure
