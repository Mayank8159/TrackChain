import cv2
import numpy as np
import base64
import httpx
import time

API_URL = "http://localhost:8000/process-frame"

def create_adversarial_image(variant):
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    # Draw some fake rails
    cv2.line(img, (200, 0), (200, 480), (255, 255, 255), 3)
    cv2.line(img, (440, 0), (440, 480), (255, 255, 255), 3)
    
    if variant == "mud":
        # 60% coverage with dark brown polygons
        for _ in range(50):
            pts = np.random.randint(0, 640, (np.random.randint(3, 6), 2))
            cv2.fillPoly(img, [pts], (20, 30, 40))
    elif variant == "monsoon":
        # Heavy blur + darkness
        img = cv2.GaussianBlur(img, (25, 25), 0)
        img = (img * 0.3).astype(np.uint8)
    elif variant == "night_glare":
        # High noise + whiteout
        noise = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        img = cv2.addWeighted(img, 0.3, noise, 0.7, 0)
        cv2.circle(img, (320, 240), 150, (255, 255, 255), -1)
        
    _, buf = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 80])
    return base64.b64encode(buf).decode('utf-8')

def test_variant(variant):
    print(f"\n--- Testing Variant: {variant.upper()} ---")
    b64 = create_adversarial_image(variant)
    payload = {"frame": b64, "camera_id": f"CHAOS-CAM-{variant}"}
    
    start = time.time()
    resp = httpx.post(API_URL, json=payload, timeout=10.0)
    latency = (time.time() - start) * 1000
    
    data = resp.json()
    print(f"Status: {resp.status_code} | Latency: {latency:.1f}ms")
    print(f"Vision Status: {data.get('vision_status')} | Score: {data.get('vision_confidence_score')}")
    print(f"Rails: {len(data.get('rails', []))} | Sleepers: {len(data.get('sleepers', []))} | YOLO: {len(data.get('yolo_boxes', []))}")
    
    if data.get('vision_status') in ['DEGRADED', 'LOW_CONFIDENCE']:
        print("✅ PASS: System honestly admitted it is blind.")
    else:
        print("❌ FAIL: System hallucinated confidence on bad data.")

if __name__ == "__main__":
    test_variant("mud")
    test_variant("monsoon")
    test_variant("night_glare")
