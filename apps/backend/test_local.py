#!/usr/bin/env python3
"""
Quick smoke-test for /process-frame endpoint.

Usage:
    # Against local SAM
    python test_local.py --url http://127.0.0.1:3000/process-frame

    # Against Docker container directly
    python test_local.py --url http://127.0.0.1:8080/process-frame

Requires: opencv-python, requests
"""

import argparse
import base64
import json
import sys

import cv2
import requests


def generate_test_frame(width: int = 640, height: int = 480) -> str:
    """Create a synthetic frame with two horizontal white lines on black."""
    img = cv2.imread(r"C:\Users\MAYANK KUMAR SHARMA\Desktop\projects\TrackChain\apps\backend\test_frame.jpg")
    if img is None:
        # Fallback: generate a synthetic frame
        img = cv2.imread
        img = __import__("numpy").zeros((height, width, 3), dtype="uint8")
        # Top rail
        cv2.line(img, (50, 150), (590, 150), (255, 255, 255), 2)
        # Bottom rail
        cv2.line(img, (50, 330), (590, 330), (255, 255, 255), 2)
        # Sleeper markers
        for x in range(100, 550, 40):
            cv2.line(img, (x, 160), (x, 320), (128, 128, 128), 1)

    _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return base64.b64encode(buf).decode("utf-8")


def main():
    parser = argparse.ArgumentParser(description="Test /process-frame endpoint")
    parser.add_argument("--url", default="http://127.0.0.1:8080/process-frame")
    parser.add_argument("--camera-id", default="test-cam-01")
    parser.add_argument("--frame", default=None, help="Path to a real frame image")
    args = parser.parse_args()

    if args.frame:
        with open(args.frame, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
    else:
        b64 = generate_test_frame()

    payload = {
        "camera_id": args.camera_id,
        "frame": b64,
    }

    print(f"POST {args.url}")
    resp = requests.post(args.url, json=payload, timeout=30)
    print(f"Status: {resp.status_code}")
    print(json.dumps(resp.json(), indent=2))

    if resp.status_code != 200:
        sys.exit(1)


if __name__ == "__main__":
    main()
