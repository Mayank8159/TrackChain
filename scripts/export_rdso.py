# Export defect & telemetry compliance reports for Indian Railways RDSO / UDM (tc.v1).

import argparse
import os
import sys
import urllib.request
from typing import Optional


def export_reports(
    backend_url: str = "http://127.0.0.1:8000",
    output_dir: str = "artifacts/reports",
    session_id: Optional[str] = None,
):
    os.makedirs(output_dir, exist_ok=True)
    print(f"[INFO] Exporting compliance reports from {backend_url}...")

    # 1. Export CSV
    csv_url = f"{backend_url}/api/v1/dashboard/export/csv"
    if session_id:
        csv_url += f"?session_id={session_id}"

    csv_path = os.path.join(output_dir, f"defects_export_{session_id or 'all'}.csv")
    try:
        urllib.request.urlretrieve(csv_url, csv_path)
        print(f"[OK] Downloaded RDSO CSV defect report: {csv_path} ({os.path.getsize(csv_path)} bytes)")
    except Exception as exc:
        print(f"[WARN] CSV export notice: {exc}")

    # 2. Export Parquet
    parquet_url = f"{backend_url}/api/v1/dashboard/export/parquet"
    if session_id:
        parquet_url += f"?session_id={session_id}"

    parquet_path = os.path.join(output_dir, f"session_analytics_{session_id or 'all'}.parquet")
    try:
        urllib.request.urlretrieve(parquet_url, parquet_path)
        print(f"[OK] Downloaded Parquet analytics dataset: {parquet_path} ({os.path.getsize(parquet_path)} bytes)")
    except Exception as exc:
        print(f"[WARN] Parquet export notice: {exc}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export RDSO track compliance reports.")
    parser.add_argument("--backend-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output-dir", default="artifacts/reports")
    parser.add_argument("--session-id", default=None)
    args = parser.parse_args()
    export_reports(args.backend_url, args.output_dir, args.session_id)
