# Tests for PostGIS / Geospatial Radius Search, CSV, and Apache Parquet Exports (tc.v1 SOTA).

import pytest
import io
import csv
import pyarrow.parquet as pq
from fastapi.testclient import TestClient
from src.main import app
from src.db.session import Base, engine, SessionLocal
from src.db.models import DefectEvent, MonitoringSession


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield


def test_geospatial_nearby_defects():
    client = TestClient(app)
    db = SessionLocal()

    # Create session
    ses = MonitoringSession(id="ses-geo-test", name="Geospatial Section", track_id="IR-GEO-01", track_section="Km 100-110")
    db.add(ses)

    # Ingest 3 defects at known coordinates:
    # Point A: 28.5350, 77.2840 (Center)
    # Point B: 28.5355, 77.2842 (~60m away - inside 200m radius)
    # Point C: 28.5900, 77.3500 (~8.5km away - outside 200m radius)
    d1 = DefectEvent(
        id="def-geo-01", session_id="ses-geo-test", defect_class="crack", severity="critical",
        chainage_m=10000.0, latitude=28.5350, longitude=77.2840, confidence=0.95, source_model="yolo_v8_detector"
    )
    d2 = DefectEvent(
        id="def-geo-02", session_id="ses-geo-test", defect_class="missing_fastener", severity="high",
        chainage_m=10060.0, latitude=28.5355, longitude=77.2842, confidence=0.91, source_model="yolo_v8_detector"
    )
    d3 = DefectEvent(
        id="def-geo-03", session_id="ses-geo-test", defect_class="spalling", severity="medium",
        chainage_m=18500.0, latitude=28.5900, longitude=77.3500, confidence=0.88, source_model="yolo_v8_detector"
    )
    db.add_all([d1, d2, d3])
    db.commit()
    db.close()

    # Query within 200m of Point A
    res = client.get("/api/v1/defects/nearby?lat=28.5350&lon=77.2840&radius_m=200")
    assert res.status_code == 200
    data = res.json()
    assert data["count"] >= 2
    ids = [d["id"] for d in data["defects"]]
    assert "def-geo-01" in ids
    assert "def-geo-02" in ids
    assert "def-geo-03" not in ids


def test_session_report_csv_export():
    client = TestClient(app)

    res = client.get("/api/v1/dashboard/export/ses-geo-test?format=csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "trackchain_session_ses-geo-test.csv" in res.headers["content-disposition"]

    # Parse CSV content
    reader = csv.DictReader(io.StringIO(res.text))
    rows = list(reader)
    assert len(rows) >= 2
    assert "defect_id" in rows[0]
    assert "severity" in rows[0]


def test_session_report_parquet_export():
    client = TestClient(app)

    res = client.get("/api/v1/dashboard/export/ses-geo-test?format=parquet")
    assert res.status_code == 200
    assert "application/octet-stream" in res.headers["content-type"]
    assert "trackchain_session_ses-geo-test.parquet" in res.headers["content-disposition"]

    # Read Parquet binary
    table = pq.read_table(io.BytesIO(res.content))
    assert table.num_rows >= 2
    assert "defect_class" in table.column_names
    assert "confidence" in table.column_names
