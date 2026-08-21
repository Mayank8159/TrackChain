import asyncio
import httpx
import time

API_URL = "http://localhost:8000/api/telemetry"

async def spam_request(client, i):
    payload = {
        "device_id": f"DDOS-NODE-{i}",
        "session_id": "ses-ddos",
        "points": [{"chainage_m": float(i), "gauge_mm": 1676.0, "cant_mm": 0.0, "timestamp": int(time.time()*1000)}]
    }
    try:
        resp = await client.post(API_URL, json=payload, timeout=5.0)
        return resp.status_code
    except Exception as e:
        return str(e)

async def main():
    print("Launching 50 concurrent telemetry requests...")
    async with httpx.AsyncClient() as client:
        tasks = [spam_request(client, i) for i in range(50)]
        results = await asyncio.gather(*tasks)
        
    status_counts = {}
    for r in results:
        status_counts[r] = status_counts.get(r, 0) + 1
        
    print("Results:", status_counts)
    
    if status_counts.get(429, 0) > 0 or status_counts.get(200, 0) == 50:
        print("✅ PASS: Backend survived. Rate limiter engaged or handled gracefully.")
    else:
        print("❌ FAIL: Backend crashed or returned 500s under load.")

if __name__ == "__main__":
    asyncio.run(main())
