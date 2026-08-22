import os
import json
import hashlib
from pathlib import Path
import boto3

# AWS Native S3 Model Artifact Registry Loader

MODEL_BUCKET = os.getenv("MODEL_BUCKET", "trackchain-models-prod")
LOCAL_MODEL_DIR = Path("/tmp/models")
LOCAL_MODEL_DIR.mkdir(parents=True, exist_ok=True)

# Lazy boto3 client
_s3_client = None
def get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client('s3')
    return _s3_client

def verify_sha256(file_path: Path, expected_hash: str) -> bool:
    with open(file_path, "rb") as f:
        actual_hash = hashlib.sha256(f.read()).hexdigest()
        return actual_hash == expected_hash

def load_artifacts() -> dict:
    """
    Downloads and verifies ONNX models, memory banks, and manifest.json 
    from the private AWS S3 bucket during backend startup.
    """
    if os.getenv("SKIP_ARTIFACT_DOWNLOAD", "").lower() == "true":
        # For local dev without AWS credentials
        print("[Artifacts] SKIP_ARTIFACT_DOWNLOAD is set. Using dummy artifact structure.")
        return {
            "calibration": {"method": "tc.v1"},
            "yolo_int8": "yolov8n_rail_best.onnx",
            "bilstm": "bilstm_fault_typing_enhanced.pt",
            "seqvae": "sequence_vae_enhanced.pt",
            "patchcore_bank": "patchcore_memory_bank.npz"
        }

    print(f"[Artifacts] Loading artifacts from s3://{MODEL_BUCKET}...")
    s3 = get_s3_client()
    
    # 1. Download manifest securely from S3
    manifest_obj = s3.get_object(Bucket=MODEL_BUCKET, Key="manifest.json")
    manifest = json.loads(manifest_obj['Body'].read().decode('utf-8'))
    
    out = {"calibration": manifest["calibration"]}
    
    # 2. Download and verify ONNX/NPZ artifacts
    for name, cfg in manifest["models"].items():
        if cfg.get("artifact"):
            artifact_key = cfg["artifact"]
            local_path = LOCAL_MODEL_DIR / artifact_key
            
            # Only download if missing or hash mismatch (caches across cold starts if /tmp persists)
            if not local_path.exists() or not verify_sha256(local_path, cfg["sha256"]):
                print(f"[Artifacts] Downloading {artifact_key} to {local_path}...")
                s3.download_file(MODEL_BUCKET, artifact_key, str(local_path))
                
                if not verify_sha256(local_path, cfg["sha256"]):
                    raise RuntimeError(f"Security violation: {artifact_key} hash mismatch!")
            
            out[name] = str(local_path)
            
    return out
