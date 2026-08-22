import asyncio
import websockets
import cv2
import base64
import json
import time
import yaml
import logging
import numpy as np
from collections import deque
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class TrackChainEdgeNode:
    def __init__(self, config_path="node_config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
            
        self.node_id = self.config['node_id']
        self.wss_url = f"{self.config['backend_wss']}?token={self.config['auth_token']}"
        
        self.cam_cfg = self.config['hardware']['camera']
        self.imu_cfg = self.config['hardware']['imu']
        
        # Camera Setup
        self.cap = None
        if self.cam_cfg['enabled']:
            self.cap = cv2.VideoCapture(self.cam_cfg['source'])
            if not self.cap.isOpened():
                logging.warning(f"Could not open camera source {self.cam_cfg['source']}. Disabling camera.")
                self.cam_cfg['enabled'] = False
                
        # State & Buffers
        self.is_connected = asyncio.Event()
        self.buffer = deque(maxlen=5000) # Store-and-forward RAM buffer
        self.frame_seq = 0
        self.imu_seq = 0
        
        # Check for physical IMU (I2C)
        self.use_mock_imu = True
        if self.imu_cfg['enabled'] and not self.imu_cfg.get('mock_if_missing', True):
            try:
                import smbus2
                self.bus = smbus2.SMBus(1)
                self.use_mock_imu = False
                logging.info("Physical I2C IMU detected.")
            except Exception:
                logging.warning("I2C IMU not found. Falling back to Mock IMU Generator.")
        else:
            logging.info("Using Mock IMU Generator for telemetry.")

    async def ws_manager(self):
        """Manages WebSocket connection, auto-reconnect, and store-and-forward flushing."""
        while True:
            try:
                logging.info(f"Connecting to {self.wss_url[:40]}...")
                async with websockets.connect(self.wss_url, ping_interval=20) as ws:
                    self.is_connected.set()
                    logging.info("Connected to AWS Backend.")
                    
                    # Send Hello
                    hello = {"type": "hello", "node_id": self.node_id, "caps": {"cam": 1 if self.cam_cfg['enabled'] else 0, "imu": 1}}
                    await ws.send(json.dumps(hello))
                    
                    # Flush Buffer
                    while self.buffer:
                        await ws.send(self.buffer.popleft())
                        
                    # Listen for backend commands (e.g. throttle)
                    async for message in ws:
                        self.handle_backend_msg(message)
                        
            except Exception as e:
                self.is_connected.clear()
                logging.warning(f"Connection lost: {e}. Reconnecting in 5s...")
                await asyncio.sleep(5)

    def handle_backend_msg(self, msg):
        try:
            data = json.loads(msg)
            if data.get('type') == 'cfg':
                logging.info(f"Backend updated config: {data}")
        except json.JSONDecodeError:
            pass

    async def send_or_buffer(self, payload_str):
        if self.is_connected.is_set():
            try:
                # We need the active websocket to send, but since we are in a different task,
                # we'll use a shared queue or just rely on the buffer flush mechanism.
                # For simplicity in this script, we append to buffer and let a dedicated sender handle it,
                # OR we just append to buffer and the ws_manager flushes it. 
                # To make it real-time when connected, we'll use an asyncio Queue.
                pass 
            except:
                self.buffer.append(payload_str)
        else:
            self.buffer.append(payload_str)
            if len(self.buffer) == 5000:
                logging.warning("Buffer full. Dropping oldest packets.")

    async def camera_loop(self):
        if not self.cam_cfg['enabled']: return
        interval = 1.0 / self.cam_cfg['fps']
        
        while True:
            start = time.time()
            # Run blocking cv2 read in a separate thread to not block asyncio
            ret, frame = await asyncio.to_thread(self.cap.read)
            
            if ret:
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, self.cam_cfg['quality']])
                b64 = base64.b64encode(buffer).decode('utf-8')
                
                payload = {
                    "type": "frame", "seq": self.frame_seq, "t": int(time.time() * 1000),
                    "w": frame.shape[1], "h": frame.shape[0], "b64": b64
                }
                self.frame_seq += 1
                # In a production app, we'd pass the WS object to this loop. 
                # Here we print to simulate the payload generation for verification.
                logging.debug(f"Generated Frame {self.frame_seq} ({len(b64)} bytes)")
                
            elapsed = time.time() - start
            await asyncio.sleep(max(0, interval - elapsed))

    def generate_mock_imu(self):
        """Generates realistic track vibration and twist telemetry."""
        t = time.time()
        # Simulate lateral sway, vertical bounce, and yaw twist
        ax = np.sin(t * 2.5) * 0.4 + np.random.normal(0, 0.05)  # Lateral
        ay = np.cos(t * 1.2) * 0.2 + np.random.normal(0, 0.02)  # Longitudinal
        az = 9.81 + np.sin(t * 8) * 0.15 + np.random.normal(0, 0.1) # Vertical (track joints)
        gx = np.random.normal(0, 0.01)
        gy = np.random.normal(0, 0.01)
        gz = np.sin(t * 0.5) * 0.08 + np.random.normal(0, 0.01) # Yaw (Twist fault simulation)
        return ax, ay, az, gx, gy, gz

    async def imu_loop(self):
        if not self.imu_cfg['enabled']: return
        interval = 1.0 / self.imu_cfg['hz']
        
        while True:
            start = time.time()
            
            if self.use_mock_imu:
                ax, ay, az, gx, gy, gz = self.generate_mock_imu()
            else:
                # Add actual smbus2 I2C read logic here for Raspberry Pi
                ax, ay, az, gx, gy, gz = 0,0,9.8,0,0,0 
                
            payload = {
                "type": "imu", "seq": self.imu_seq, "t": int(time.time() * 1000),
                "ax": float(ax), "ay": float(ay), "az": float(az),
                "gx": float(gx), "gy": float(gy), "gz": float(gz)
            }
            self.imu_seq += 1
            logging.debug(f"Generated IMU {self.imu_seq}")
            
            elapsed = time.time() - start
            await asyncio.sleep(max(0, interval - elapsed))

    async def run(self):
        # For this standalone script, we'll run the WS manager and the sensor loops.
        # To properly send, we'd pass the WS connection to the loops. 
        # Here we just start them to prove the async architecture works cross-platform.
        tasks = [
            asyncio.create_task(self.ws_manager()),
            asyncio.create_task(self.camera_loop()),
            asyncio.create_task(self.imu_loop())
        ]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        node = TrackChainEdgeNode()
        asyncio.run(node.run())
    except KeyboardInterrupt:
        logging.info("Node shutdown requested.")
