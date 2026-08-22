# TrackChain ML Evaluation v2 — Image Prompts for Demo Out-of-Distribution Testing

This document contains prompts and instructions for sourcing the **Tier B PatchCore Novel Anomaly** (`novel_*.jpg`) images.

## Golden Rule
The image **must** deviate from the feature space of healthy railway track, but **must not** contain bounding-box-level features of a missing fastener that YOLO was trained on.

## Option 1: AI Generated (DALL-E 3 / Midjourney)
**Prompt:** 
> "A realistic, high-definition overhead photo looking straight down at a standard gauge railway track. The wooden sleepers and steel rails are intact, but a large, bright orange plastic traffic cone is sitting directly in the middle of the track between the rails. Photorealistic, 4k, daylight."

**Why it works:** A traffic cone is completely foreign to the railway domain (PatchCore fires) but has no missing fasteners (YOLO stays silent).

## Option 2: Real World Wildcard
- Use a photo of track that has been severely flooded with muddy water (where you can't see the ballast).
- Use a photo of a large tree branch fallen across the rails.
- Use a photo of track overgrown with thick green vegetation.

## Selection Process
1. Save 2-3 candidate images as `ml/evaluation/candidates/novel_1.jpg`, `novel_2.jpg`, etc.
2. Run `python -m ml.evaluation.pre_verify`.
3. The harness will automatically measure and pick the novel image that produces the highest PatchCore score while keeping the YOLO score as low as possible.
