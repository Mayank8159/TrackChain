import base64
import json
import urllib.request
import io
from PIL import Image

# Create a small blank image (since we just need to see if it processes)
img = Image.new('RGB', (640, 480), color = 'gray')
buf = io.BytesIO()
img.save(buf, format='JPEG')
img_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')

payload = {"frame": img_b64, "trace_id": "test"}
req = urllib.request.Request("http://localhost:8000/process-frame", data=json.dumps(payload).encode(), method="POST")
req.add_header("Content-Type", "application/json")
try:
    with urllib.request.urlopen(req) as r:
        resp = json.loads(r.read())
        print("HOUGH Inference MS:", resp.get("inference_ms"))
        print("Rails:", len(resp.get("rails", [])))
        print("Sleepers:", len(resp.get("sleepers", [])))
except urllib.error.HTTPError as e:
    print(f"422 ERROR: {e.read().decode()}")
except Exception as e:
    print(f"ERROR: {e}")
