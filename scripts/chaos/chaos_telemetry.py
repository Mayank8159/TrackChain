import httpx
import numpy as np
import time

API_URL = "http://localhost:8000/api/telemetry"
DEVICE_ID = "CHAOS-BOGIE-01"

def generate_noisy_telemetry(count=500):
    points = []
    base_chainage = 1000.0
    for i in range(count):
        # Perfectly straight track, but violent high-frequency IMU noise
        points.append({
            "chainage_m": base_chainage + i,
            "gauge_mm": 1676 + float(np.random.normal(0, 15)), # 15mm std dev noise
            "cant_mm": float(np.random.normal(0, 25)),         # 25mm std dev noise
            "twist_mm_per_m": float(np.random.normal(0, 5)),
            "vertical_unevenness_mm": float(np.random.normal(0, 10)),
            "timestamp": int(time.time() * 1000) + i
        })
    return points

if __name__ == "__main__":
    print("Injecting 500 high-noise telemetry points...")
    payload = {
        "device_id": DEVICE_ID,
        "session_id": "ses-chaos-test",
        "points": generate_noisy_telemetry()
    }
    
    start = time.time()
    resp = httpx.post(API_URL, json=payload, timeout=15.0)
    latency = (time.time() - start) * 1000
    
    print(f"Status: {resp.status_code} | Latency: {latency:.1f}ms")
    
    # Check if it triggered a false positive flood
    defects_resp = httpx.get("http://localhost:8000/api/defects?session_id=ses-chaos-test")
    defects = defects_resp.json() if defects_resp.status_code == 200 else []
    print(f"Defects Generated: {len(defects)}")
    
    if len(defects) < 10:
        print("✅ PASS: Isolation Forest filtered out high-frequency noise. No false-positive flood.")
    else:
        print("❌ FAIL: System flagged every vibration as a defect. Tune contamination threshold!")
