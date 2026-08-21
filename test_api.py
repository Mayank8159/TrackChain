import urllib.request
import urllib.error
import json

BASE_URL = "http://localhost:8000"

def test_endpoint(path, expected_status=200):
    try:
        req = urllib.request.Request(f"{BASE_URL}{path}")
        with urllib.request.urlopen(req) as r:
            print(f"GET {path} -> {r.status}")
    except urllib.error.HTTPError as e:
        print(f"GET {path} -> {e.code} (Expected {expected_status})")
    except Exception as e:
        print(f"GET {path} -> ERROR: {e}")

test_endpoint("/api/sessions")
test_endpoint("/api/defects")
test_endpoint("/api/telemetry?session_id=mock")
test_endpoint("/api/dashboard/summary")
test_endpoint("/api/dashboard/performance")

try:
    req = urllib.request.Request(f"{BASE_URL}/api/alerts/stream")
    with urllib.request.urlopen(req) as r:
        print(f"GET /api/alerts/stream -> {r.status}, Content-Type: {r.headers.get('Content-Type')}")
except Exception as e:
    print(f"GET /api/alerts/stream -> ERROR: {e}")

print("Testing POST Ingestion:")
try:
    req = urllib.request.Request(f"{BASE_URL}/api/telemetry", data=b'{"bad": "data"}', method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req) as r:
        print(f"POST /api/telemetry (bad payload) -> {r.status}")
except urllib.error.HTTPError as e:
    print(f"POST /api/telemetry (bad payload) -> {e.code} {e.read().decode()[:100]}")
except Exception as e:
    print(f"POST /api/telemetry (bad payload) -> ERROR: {e}")
