import asyncio
import numpy as np
from src.services.ingest import frame_q, imu_q

class MLPipeline:
    def __init__(self, artifacts: dict):
        # We simulate ONNX session loading since this is just architectural wiring
        self.artifacts = artifacts
        print(f"[MLPipeline] Initialized with artifacts: {list(artifacts.keys())}")

    async def worker(self):
        print("[MLPipeline] Worker started")
        while True:
            # Simple simulation: drain queues periodically
            frames = []
            while not frame_q.empty():
                frames.append(await frame_q.get())
                
            imus = []
            while not imu_q.empty():
                imus.append(await imu_q.get())

            if frames or imus:
                # Process the segment
                # In real app: YOLO -> PatchCore -> Physics -> BiLSTM -> Seq-VAE -> Fuse
                print(f"[MLPipeline] Processed segment: {len(frames)} frames, {len(imus)} imu")
                
                # Broadcast live frames (simulate defect event)
                for f in frames:
                    from src.gateway.live_ws import broadcast_live_event
                    
                    # Convert raw bytes back to base64 for frontend
                    import base64
                    b64_frame = base64.b64encode(f.raw).decode('utf-8')
                    
                    await broadcast_live_event({
                        "type": "frame",
                        "b64": b64_frame,
                        "t": f.t,
                        "chainage": f.chainage
                    })
                    
            await asyncio.sleep(0.5)

async def start_worker(artifacts: dict) -> asyncio.Task:
    pipeline = MLPipeline(artifacts)
    return asyncio.create_task(pipeline.worker())
