#!/bin/bash
# Upload local trained models and manifest to AWS S3 Model Registry

MODEL_BUCKET="s3://trackchain-models-prod"

echo "Uploading TrackChain ML Artifacts to $MODEL_BUCKET..."

# 1. Upload the Manifest
aws s3 cp artifacts/calibration/manifest.json $MODEL_BUCKET/manifest.json

# 2. Upload Vision Models
aws s3 cp artifacts/exports/yolov8n_rail_best_int8.onnx $MODEL_BUCKET/
aws s3 cp artifacts/checkpoints/vision/patchcore_memory_bank.npz $MODEL_BUCKET/

# 3. Upload Geometry Models
aws s3 cp artifacts/exports/bilstm_fault_typing_enhanced.onnx $MODEL_BUCKET/
aws s3 cp artifacts/exports/sequence_vae_enhanced.onnx $MODEL_BUCKET/

echo "Upload complete! The Fargate ECS tasks will pull these automatically on startup via their IAM role."
