# ORM models: telemetry, defects, sessions, media metadata.

import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    DateTime,
    ForeignKey,
    Text,
    Enum,
    JSON,
)
from sqlalchemy.orm import relationship
from src.db.session import Base


class MonitoringSession(Base):
    __tablename__ = "monitoring_sessions"

    id = Column(String(64), primary_key=True, default=lambda: f"ses-{uuid.uuid4().hex[:12]}")
    name = Column(String(255), nullable=False)
    track_id = Column(String(128), nullable=False, index=True)
    track_section = Column(String(255), nullable=False)
    start_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    end_time = Column(DateTime, nullable=True)
    status = Column(String(32), default="active", nullable=False)
    total_distance_km = Column(Float, default=0.0)
    defects_count = Column(Integer, default=0)
    operator_name = Column(String(128), nullable=True)

    telemetry_records = relationship("TelemetryRecord", back_populates="session", cascade="all, delete-orphan")
    defect_events = relationship("DefectEvent", back_populates="session", cascade="all, delete-orphan")


class TelemetryRecord(Base):
    __tablename__ = "telemetry_records"

    id = Column(String(64), primary_key=True, default=lambda: f"tel-{uuid.uuid4().hex[:12]}")
    session_id = Column(String(64), ForeignKey("monitoring_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    chainage_m = Column(Float, nullable=False, index=True)
    speed_kmh = Column(Float, default=0.0)
    vibration_rms = Column(Float, default=0.0)
    track_gauge_mm = Column(Float, default=1435.0)
    cant_mm = Column(Float, default=0.0)
    twist_mm_per_m = Column(Float, default=0.0)
    vertical_unevenness_mm = Column(Float, default=0.0)
    alignment_dev_mm = Column(Float, default=0.0)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    session = relationship("MonitoringSession", back_populates="telemetry_records")


class DefectEvent(Base):
    __tablename__ = "defect_events"

    id = Column(String(64), primary_key=True, default=lambda: f"def-{uuid.uuid4().hex[:12]}")
    session_id = Column(String(64), ForeignKey("monitoring_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    chainage_m = Column(Float, nullable=False, index=True)
    defect_class = Column(String(64), nullable=False, index=True)
    severity = Column(String(32), nullable=False, index=True)
    confidence = Column(Float, nullable=False)
    stream_source = Column(String(32), nullable=False)  # vision, geometry, fused
    image_url = Column(String(512), nullable=True)
    video_timestamp_sec = Column(Float, nullable=True)
    description = Column(Text, nullable=True)
    status = Column(String(32), default="open", nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    session = relationship("MonitoringSession", back_populates="defect_events")


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id = Column(String(64), primary_key=True, default=lambda: f"med-{uuid.uuid4().hex[:12]}")
    session_id = Column(String(64), ForeignKey("monitoring_sessions.id", ondelete="CASCADE"), nullable=True)
    filename = Column(String(255), nullable=False)
    s3_key = Column(String(512), nullable=False)
    content_type = Column(String(64), nullable=False)
    size_bytes = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
