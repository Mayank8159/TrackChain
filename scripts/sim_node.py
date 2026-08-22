import asyncio
import websockets
import json
import time
import base64
import os
import random
import cv2

NODE_ID = "TC-NODE-SIM"
TOKEN = "SECRET_TOKEN"
WS_URL = f"ws://localhost:8000/ws/node?token={TOKEN}"

async def simulate_node():
    """
    Simulates an ESP32-CAM node pushing Base64 frames and IMU data to the backend.
    """
    print(f"Connecting to {WS_URL}...")
    
    try:
        async with websockets.connect(WS_URL) as ws:
            print("Connected! Sending hello...")
            await ws.send(json.dumps({
                "type": "hello",
                "node_id": NODE_ID,
                "fw": "1.0-sim"
            }))
            
            # Start background task to receive ack/cfg
            async def rx_loop():
                try:
                    async for msg in ws:
                        print(f"RX: {msg}")
                except websockets.exceptions.ConnectionClosed:
                    print("Connection closed by server")
            
            asyncio.create_task(rx_loop())
            
            # Create a blank dummy image to send
            img = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(img, "SIMULATED FRAME", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            _, buf = cv2.imencode('.jpg', img)
            b64_frame = base64.b64encode(buf).decode('utf-8')
            
            frame_seq = 0
            imu_seq = 0
            
            while True:
                now = int(time.time() * 1000)
                
                # Send IMU (simulate 20Hz)
                if imu_seq % 4 == 0:  # Every 4th tick send a frame (5 fps)
                    await ws.send(json.dumps({
                        "type": "frame",
                        "t": now,
                        "seq": frame_seq,
                        "w": 640,
                        "h": 480,
                        "b64": b64_frame
                    }))
                    frame_seq += 1
                
                await ws.send(json.dumps({
                    "type": "imu",
                    "t": now,
                    "seq": imu_seq,
                    "ax": random.gauss(0, 0.1),
                    "ay": random.gauss(0, 0.1),
                    "az": random.gauss(9.8, 0.1),
                    "gx": random.gauss(0, 0.01),
                    "gy": random.gauss(0, 0.01),
                    "gz": random.gauss(0, 0.01),
                    "speed": 15.0 # m/s
                }))
                
                if imu_seq % 100 == 0:
                    await ws.send(json.dumps({"type": "hb", "t": now}))
                    
                imu_seq += 1
                await asyncio.sleep(0.05)  # 50ms = 20Hz
                
    except Exception as e:
        print(f"Simulation error: {e}")

if __name__ == "__main__":
    import numpy as np
    asyncio.run(simulate_node())
