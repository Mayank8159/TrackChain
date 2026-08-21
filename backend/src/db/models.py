# ORM models: devices, sessions, track_segments, telemetry, media, ml_signals, defects, calibration, registry, alerts, ingestion_keys (tc.v1 SOTA).

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    Index,
)
from sqlalchemy.orm import relationship
from src.db.session import Base


def utc_now():
    """Return current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class IngestionKey(Base):
    __tablename__ = "ingestion_keys"

    idempotency_key = Column(String(128), primary_key=True)
    entity_type = Column(String(32), nullable=False)  # telemetry, defects, ml_signals
    entity_id = Column(String(64), nullable=True)
    response_payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)


class Device(Base):
    __tablename__ = "devices"

    device_id = Column(String(64), primary_key=True)
    device_name = Column(String(128), nullable=False)
    hardware_version = Column(String(64), nullable=False)
    firmware_version = Column(String(64), nullable=False)
    camera_model = Column(String(128), nullable=True)
    imu_model = Column(String(128), nullable=True)
    gnss_model = Column(String(128), nullable=True)
    status = Column(String(32), default="offline", nullable=False)
    api_key_hash = Column(String(256), nullable=True)
    battery_voltage_v = Column(Float, nullable=True)
    cpu_temp_c = Column(Float, nullable=True)
    last_seen_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    sessions = relationship("MonitoringSession", back_populates="device")


class MonitoringSession(Base):
    __tablename__ = "sessions"

    id = Column(String(64), primary_key=True, default=lambda: f"ses-{uuid.uuid4().hex[:12]}")
    device_id = Column(String(64), ForeignKey("devices.device_id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    route_name = Column(String(128), nullable=True)
    line_name = Column(String(128), nullable=True)
    track_id = Column(String(128), nullable=False, index=True)
    track_section = Column(String(255), nullable=False)
    track_direction = Column(String(16), default="both", nullable=False)
    start_time = Column(DateTime, default=utc_now, nullable=False)
    end_time = Column(DateTime, nullable=True)
    start_chainage_m = Column(Float, default=0.0)
    end_chainage_m = Column(Float, default=0.0)
    status = Column(String(32), default="created", nullable=False)
    total_distance_km = Column(Float, default=0.0)
    defects_count = Column(Integer, default=0)
    operator_name = Column(String(128), nullable=True)
    weather = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    device = relationship("Device", back_populates="sessions")
    segments = relationship("TrackSegment", back_populates="session", cascade="all, delete-orphan")
    telemetry_records = relationship("TelemetryRecord", back_populates="session", cascade="all, delete-orphan")
    media_assets = relationship("MediaAsset", back_populates="session", cascade="all, delete-orphan")
    ml_signals = relationship("MLSignal", back_populates="session", cascade="all, delete-orphan")
    defect_events = relationship("DefectEvent", back_populates="session", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="session", cascade="all, delete-orphan")


class TrackSegment(Base):
    __tablename__ = "track_segments"

    segment_id = Column(String(64), primary_key=True, default=lambda: f"seg-{uuid.uuid4().hex[:12]}")
    session_id = Column(String(64), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    chainage_start_m = Column(Float, nullable=False, index=True)
    chainage_end_m = Column(Float, nullable=False, index=True)
    timestamp_start = Column(DateTime, nullable=False)
    timestamp_end = Column(DateTime, nullable=False)
    lat_start = Column(Float, nullable=True)
    lon_start = Column(Float, nullable=True)
    lat_end = Column(Float, nullable=True)
    lon_end = Column(Float, nullable=True)
    speed_avg_mps = Column(Float, default=0.0)

    session = relationship("MonitoringSession", back_populates="segments")
    telemetry_samples = relationship("TelemetryRecord", back_populates="segment")
    ml_signals = relationship("MLSignal", back_populates="segment")
    defect_events = relationship("DefectEvent", back_populates="segment")


class TelemetryRecord(Base):
    __tablename__ = "telemetry_samples"

    id = Column(String(64), primary_key=True, default=lambda: f"tel-{uuid.uuid4().hex[:12]}")
    session_id = Column(String(64), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id = Column(String(64), ForeignKey("devices.device_id", ondelete="SET NULL"), nullable=True)
    segment_id = Column(String(64), ForeignKey("track_segments.segment_id", ondelete="SET NULL"), nullable=True, index=True)
    timestamp = Column(DateTime, default=utc_now, nullable=False, index=True)
    chainage_m = Column(Float, nullable=False, index=True)

    # Spatial & Kinematics
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    altitude_m = Column(Float, nullable=True)
    gnss_fix_quality = Column(Integer, nullable=True)
    gnss_satellites = Column(Integer, nullable=True)
    speed_mps = Column(Float, default=0.0)
    speed_kmh = Column(Float, default=0.0)

    # IMU Data
    imu_ax = Column(Float, nullable=True)
    imu_ay = Column(Float, nullable=True)
    imu_az = Column(Float, nullable=True)
    imu_gx = Column(Float, nullable=True)
    imu_gy = Column(Float, nullable=True)
    imu_gz = Column(Float, nullable=True)
    roll_deg = Column(Float, nullable=True)
    pitch_deg = Column(Float, nullable=True)
    yaw_deg = Column(Float, nullable=True)

    # Dynamics & EN 13848 Track Geometry
    vertical_rms = Column(Float, default=0.0)
    lateral_rms = Column(Float, default=0.0)
    longitudinal_rms = Column(Float, default=0.0)
    vibration_rms = Column(Float, default=0.0)
    vibration_index = Column(Float, default=0.0)
    track_gauge_mm = Column(Float, default=1435.0)
    cant_mm = Column(Float, default=0.0)
    twist_mm_per_m = Column(Float, default=0.0)
    vertical_unevenness_mm = Column(Float, default=0.0)
    alignment_dev_mm = Column(Float, default=0.0)

    # Diagnostics
    temperature_c = Column(Float, nullable=True)
    battery_voltage_v = Column(Float, nullable=True)

    session = relationship("MonitoringSession", back_populates="telemetry_records")
    segment = relationship("TrackSegment", back_populates="telemetry_samples")


class MediaAsset(Base):
    __tablename__ = "media_assets"

    media_id = Column(String(64), primary_key=True, default=lambda: f"med-{uuid.uuid4().hex[:12]}")
    session_id = Column(String(64), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id = Column(String(64), ForeignKey("devices.device_id", ondelete="SET NULL"), nullable=True)
    segment_id = Column(String(64), ForeignKey("track_segments.segment_id", ondelete="SET NULL"), nullable=True)
    media_type = Column(String(32), nullable=False)  # video_segment, evidence_image, thumbnail, report_file
    s3_bucket = Column(String(128), nullable=False)
    s3_key = Column(String(512), nullable=False)
    content_type = Column(String(64), nullable=False)
    size_bytes = Column(Integer, default=0)
    duration_seconds = Column(Float, nullable=True)
    timestamp_start = Column(DateTime, nullable=True)
    timestamp_end = Column(DateTime, nullable=True)
    chainage_start_m = Column(Float, nullable=True)
    chainage_end_m = Column(Float, nullable=True)
    upload_status = Column(String(32), default="pending", nullable=False)
    checksum = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    session = relationship("MonitoringSession", back_populates="media_assets")


class MLSignal(Base):
    __tablename__ = "ml_signals"

    signal_id = Column(String(64), primary_key=True, default=lambda: f"sig-{uuid.uuid4().hex[:12]}")
    session_id = Column(String(64), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    segment_id = Column(String(64), ForeignKey("track_segments.segment_id", ondelete="CASCADE"), nullable=True, index=True)
    defect_id = Column(String(64), ForeignKey("defect_events.id", ondelete="CASCADE"), nullable=True, index=True)
    model_name = Column(String(64), nullable=False, index=True)
    model_version = Column(String(32), nullable=False)
    signal_type = Column(String(32), nullable=False)  # visual_known, visual_novel, geometry_known, geometry_novel
    raw_score = Column(Float, nullable=False)
    calibrated_score = Column(Float, nullable=False)
    threshold = Column(Float, nullable=False)
    fired = Column(Boolean, default=False, nullable=False)
    label = Column(String(64), nullable=True)
    bbox = Column(JSON, nullable=True)  # [x1, y1, x2, y2]
    explanation = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=utc_now, nullable=False)

    session = relationship("MonitoringSession", back_populates="ml_signals")
    segment = relationship("TrackSegment", back_populates="ml_signals")
    defect = relationship("DefectEvent", back_populates="supporting_signals")


class DefectEvent(Base):
    __tablename__ = "defect_events"

    id = Column(String(64), primary_key=True, default=lambda: f"def-{uuid.uuid4().hex[:12]}")
    session_id = Column(String(64), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id = Column(String(64), ForeignKey("devices.device_id", ondelete="SET NULL"), nullable=True)
    segment_id = Column(String(64), ForeignKey("track_segments.segment_id", ondelete="SET NULL"), nullable=True, index=True)

    defect_class = Column(String(64), nullable=False, index=True)
    defect_family = Column(String(32), default="visual_component", nullable=False)
    severity = Column(String(32), nullable=False, index=True)
    decision = Column(String(32), default="INSPECT_KNOWN", nullable=False)

    chainage_m = Column(Float, nullable=False, index=True)
    chainage_start_m = Column(Float, nullable=True)
    chainage_end_m = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=utc_now, nullable=False, index=True)

    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    confidence = Column(Float, nullable=False)
    source_model = Column(String(64), nullable=False)
    model_version = Column(String(32), nullable=True)
    stream_source = Column(String(32), default="fused", nullable=False)

    image_url = Column(String(512), nullable=True)
    evidence_image_id = Column(String(64), nullable=True)
    video_media_id = Column(String(64), nullable=True)
    video_timestamp_sec = Column(Float, nullable=True)
    video_offset_seconds = Column(Float, nullable=True)

    description = Column(Text, nullable=True)
    status = Column(String(32), default="open", nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String(128), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    session = relationship("MonitoringSession", back_populates="defect_events")
    segment = relationship("TrackSegment", back_populates="defect_events")
    supporting_signals = relationship("MLSignal", back_populates="defect", cascade="all, delete-orphan")


class CalibrationArtifact(Base):
    __tablename__ = "calibration_artifacts"

    calibration_id = Column(String(64), primary_key=True, default=lambda: f"cal-{uuid.uuid4().hex[:12]}")
    model_name = Column(String(64), nullable=False, index=True)
    model_version = Column(String(32), nullable=False)
    method = Column(String(32), nullable=False)  # temperature_scaling, fpr_threshold, manual_threshold
    target_fpr = Column(Float, nullable=False)
    threshold = Column(Float, nullable=False)
    temperature = Column(Float, nullable=True)
    validation_dataset = Column(String(255), nullable=False)
    metrics_summary = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)


class ModelRegistry(Base):
    __tablename__ = "model_registry"

    model_name = Column(String(64), primary_key=True)
    model_version = Column(String(32), primary_key=True)
    model_type = Column(String(32), nullable=False)  # detector, anomaly, classifier
    artifact_uri = Column(String(512), nullable=False)
    input_contract_version = Column(String(32), default="tc.v1", nullable=False)
    output_contract_version = Column(String(32), default="tc.v1", nullable=False)
    trained_on = Column(String(255), nullable=True)
    metrics = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String(64), primary_key=True, default=lambda: f"alt-{uuid.uuid4().hex[:12]}")
    session_id = Column(String(64), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    defect_id = Column(String(64), ForeignKey("defect_events.id", ondelete="CASCADE"), nullable=True)
    severity = Column(String(32), nullable=False)
    message = Column(String(255), nullable=False)
    acknowledged = Column(Boolean, default=False, nullable=False)
    acknowledged_by = Column(String(128), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    session = relationship("MonitoringSession", back_populates="alerts")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=utc_now, nullable=False, index=True)
    actor_type = Column(String(32), nullable=False)  # device, user, system
    actor_id = Column(String(64), nullable=False, index=True)
    action = Column(String(64), nullable=False, index=True)  # device.registered, defect.created, session.started
    resource_type = Column(String(64), nullable=True)  # device, defect, session, media
    resource_id = Column(String(64), nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(256), nullable=True)
