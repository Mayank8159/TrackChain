"""Initial schema migration with tc.v1 models and SOTA tables

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-08-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Ingestion Keys
    op.create_table(
        'ingestion_keys',
        sa.Column('idempotency_key', sa.String(length=128), primary_key=True),
        sa.Column('entity_type', sa.String(length=32), nullable=False),
        sa.Column('entity_id', sa.String(length=64), nullable=True),
        sa.Column('response_payload', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # 2. Devices
    op.create_table(
        'devices',
        sa.Column('device_id', sa.String(length=64), primary_key=True),
        sa.Column('device_name', sa.String(length=128), nullable=False),
        sa.Column('hardware_version', sa.String(length=64), nullable=False),
        sa.Column('firmware_version', sa.String(length=64), nullable=False),
        sa.Column('camera_model', sa.String(length=128), nullable=True),
        sa.Column('imu_model', sa.String(length=128), nullable=True),
        sa.Column('gnss_model', sa.String(length=128), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('api_key_hash', sa.String(length=256), nullable=True),
        sa.Column('battery_voltage_v', sa.Float(), nullable=True),
        sa.Column('cpu_temp_c', sa.Float(), nullable=True),
        sa.Column('last_seen_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # 3. Sessions
    op.create_table(
        'sessions',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('device_id', sa.String(length=64), sa.ForeignKey('devices.device_id', ondelete='SET NULL'), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('route_name', sa.String(length=128), nullable=True),
        sa.Column('line_name', sa.String(length=128), nullable=True),
        sa.Column('track_id', sa.String(length=128), nullable=False),
        sa.Column('track_section', sa.String(length=255), nullable=False),
        sa.Column('track_direction', sa.String(length=16), nullable=False),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=True),
        sa.Column('start_chainage_m', sa.Float(), nullable=True),
        sa.Column('end_chainage_m', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('total_distance_km', sa.Float(), nullable=True),
        sa.Column('defects_count', sa.Integer(), nullable=True),
        sa.Column('operator_name', sa.String(length=128), nullable=True),
        sa.Column('weather', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_sessions_device_id', 'sessions', ['device_id'])
    op.create_index('ix_sessions_track_id', 'sessions', ['track_id'])

    # 4. Track Segments
    op.create_table(
        'track_segments',
        sa.Column('segment_id', sa.String(length=64), primary_key=True),
        sa.Column('session_id', sa.String(length=64), sa.ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('chainage_start_m', sa.Float(), nullable=False),
        sa.Column('chainage_end_m', sa.Float(), nullable=False),
        sa.Column('timestamp_start', sa.DateTime(), nullable=False),
        sa.Column('timestamp_end', sa.DateTime(), nullable=False),
        sa.Column('lat_start', sa.Float(), nullable=True),
        sa.Column('lon_start', sa.Float(), nullable=True),
        sa.Column('lat_end', sa.Float(), nullable=True),
        sa.Column('lon_end', sa.Float(), nullable=True),
        sa.Column('speed_avg_mps', sa.Float(), nullable=True),
    )
    op.create_index('ix_track_segments_session_id', 'track_segments', ['session_id'])
    op.create_index('ix_track_segments_chainage_start_m', 'track_segments', ['chainage_start_m'])
    op.create_index('ix_track_segments_chainage_end_m', 'track_segments', ['chainage_end_m'])

    # 5. Telemetry Samples
    op.create_table(
        'telemetry_samples',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('session_id', sa.String(length=64), sa.ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('device_id', sa.String(length=64), sa.ForeignKey('devices.device_id', ondelete='SET NULL'), nullable=True),
        sa.Column('segment_id', sa.String(length=64), sa.ForeignKey('track_segments.segment_id', ondelete='SET NULL'), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('chainage_m', sa.Float(), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('altitude_m', sa.Float(), nullable=True),
        sa.Column('gnss_fix_quality', sa.Integer(), nullable=True),
        sa.Column('gnss_satellites', sa.Integer(), nullable=True),
        sa.Column('speed_mps', sa.Float(), nullable=True),
        sa.Column('speed_kmh', sa.Float(), nullable=True),
        sa.Column('imu_ax', sa.Float(), nullable=True),
        sa.Column('imu_ay', sa.Float(), nullable=True),
        sa.Column('imu_az', sa.Float(), nullable=True),
        sa.Column('imu_gx', sa.Float(), nullable=True),
        sa.Column('imu_gy', sa.Float(), nullable=True),
        sa.Column('imu_gz', sa.Float(), nullable=True),
        sa.Column('roll_deg', sa.Float(), nullable=True),
        sa.Column('pitch_deg', sa.Float(), nullable=True),
        sa.Column('yaw_deg', sa.Float(), nullable=True),
        sa.Column('vertical_rms', sa.Float(), nullable=True),
        sa.Column('lateral_rms', sa.Float(), nullable=True),
        sa.Column('longitudinal_rms', sa.Float(), nullable=True),
        sa.Column('vibration_rms', sa.Float(), nullable=True),
        sa.Column('vibration_index', sa.Float(), nullable=True),
        sa.Column('track_gauge_mm', sa.Float(), nullable=True),
        sa.Column('cant_mm', sa.Float(), nullable=True),
        sa.Column('twist_mm_per_m', sa.Float(), nullable=True),
        sa.Column('vertical_unevenness_mm', sa.Float(), nullable=True),
        sa.Column('alignment_dev_mm', sa.Float(), nullable=True),
        sa.Column('temperature_c', sa.Float(), nullable=True),
        sa.Column('battery_voltage_v', sa.Float(), nullable=True),
    )
    op.create_index('ix_telemetry_session_id', 'telemetry_samples', ['session_id'])
    op.create_index('ix_telemetry_segment_id', 'telemetry_samples', ['segment_id'])
    op.create_index('ix_telemetry_timestamp', 'telemetry_samples', ['timestamp'])
    op.create_index('ix_telemetry_chainage_m', 'telemetry_samples', ['chainage_m'])

    # 6. Defect Events
    op.create_table(
        'defect_events',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('session_id', sa.String(length=64), sa.ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('device_id', sa.String(length=64), sa.ForeignKey('devices.device_id', ondelete='SET NULL'), nullable=True),
        sa.Column('segment_id', sa.String(length=64), sa.ForeignKey('track_segments.segment_id', ondelete='SET NULL'), nullable=True),
        sa.Column('defect_class', sa.String(length=64), nullable=False),
        sa.Column('defect_family', sa.String(length=32), nullable=False),
        sa.Column('severity', sa.String(length=32), nullable=False),
        sa.Column('decision', sa.String(length=32), nullable=False),
        sa.Column('chainage_m', sa.Float(), nullable=False),
        sa.Column('chainage_start_m', sa.Float(), nullable=True),
        sa.Column('chainage_end_m', sa.Float(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('source_model', sa.String(length=64), nullable=False),
        sa.Column('model_version', sa.String(length=32), nullable=True),
        sa.Column('stream_source', sa.String(length=32), nullable=False),
        sa.Column('image_url', sa.String(length=512), nullable=True),
        sa.Column('evidence_image_id', sa.String(length=64), nullable=True),
        sa.Column('video_media_id', sa.String(length=64), nullable=True),
        sa.Column('video_timestamp_sec', sa.Float(), nullable=True),
        sa.Column('video_offset_seconds', sa.Float(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.Column('acknowledged_by', sa.String(length=128), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
    )
    op.create_index('ix_defect_events_session_id', 'defect_events', ['session_id'])
    op.create_index('ix_defect_events_segment_id', 'defect_events', ['segment_id'])
    op.create_index('ix_defect_events_defect_class', 'defect_events', ['defect_class'])
    op.create_index('ix_defect_events_severity', 'defect_events', ['severity'])
    op.create_index('ix_defect_events_chainage_m', 'defect_events', ['chainage_m'])
    op.create_index('ix_defect_events_timestamp', 'defect_events', ['timestamp'])

    # 7. ML Signals
    op.create_table(
        'ml_signals',
        sa.Column('signal_id', sa.String(length=64), primary_key=True),
        sa.Column('session_id', sa.String(length=64), sa.ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('segment_id', sa.String(length=64), sa.ForeignKey('track_segments.segment_id', ondelete='CASCADE'), nullable=True),
        sa.Column('defect_id', sa.String(length=64), sa.ForeignKey('defect_events.id', ondelete='CASCADE'), nullable=True),
        sa.Column('model_name', sa.String(length=64), nullable=False),
        sa.Column('model_version', sa.String(length=32), nullable=False),
        sa.Column('signal_type', sa.String(length=32), nullable=False),
        sa.Column('raw_score', sa.Float(), nullable=False),
        sa.Column('calibrated_score', sa.Float(), nullable=False),
        sa.Column('threshold', sa.Float(), nullable=False),
        sa.Column('fired', sa.Boolean(), nullable=False),
        sa.Column('label', sa.String(length=64), nullable=True),
        sa.Column('bbox', sa.JSON(), nullable=True),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_ml_signals_session_id', 'ml_signals', ['session_id'])
    op.create_index('ix_ml_signals_segment_id', 'ml_signals', ['segment_id'])
    op.create_index('ix_ml_signals_defect_id', 'ml_signals', ['defect_id'])
    op.create_index('ix_ml_signals_model_name', 'ml_signals', ['model_name'])

    # 8. Media Assets
    op.create_table(
        'media_assets',
        sa.Column('media_id', sa.String(length=64), primary_key=True),
        sa.Column('session_id', sa.String(length=64), sa.ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('device_id', sa.String(length=64), sa.ForeignKey('devices.device_id', ondelete='SET NULL'), nullable=True),
        sa.Column('segment_id', sa.String(length=64), sa.ForeignKey('track_segments.segment_id', ondelete='SET NULL'), nullable=True),
        sa.Column('media_type', sa.String(length=32), nullable=False),
        sa.Column('s3_bucket', sa.String(length=128), nullable=False),
        sa.Column('s3_key', sa.String(length=512), nullable=False),
        sa.Column('content_type', sa.String(length=64), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('timestamp_start', sa.DateTime(), nullable=True),
        sa.Column('timestamp_end', sa.DateTime(), nullable=True),
        sa.Column('chainage_start_m', sa.Float(), nullable=True),
        sa.Column('chainage_end_m', sa.Float(), nullable=True),
        sa.Column('upload_status', sa.String(length=32), nullable=False),
        sa.Column('checksum', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_media_assets_session_id', 'media_assets', ['session_id'])

    # 9. Calibration Artifacts
    op.create_table(
        'calibration_artifacts',
        sa.Column('calibration_id', sa.String(length=64), primary_key=True),
        sa.Column('model_name', sa.String(length=64), nullable=False),
        sa.Column('model_version', sa.String(length=32), nullable=False),
        sa.Column('method', sa.String(length=32), nullable=False),
        sa.Column('target_fpr', sa.Float(), nullable=False),
        sa.Column('threshold', sa.Float(), nullable=False),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('validation_dataset', sa.String(length=255), nullable=False),
        sa.Column('metrics_summary', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_calibration_model_name', 'calibration_artifacts', ['model_name'])

    # 10. Model Registry
    op.create_table(
        'model_registry',
        sa.Column('model_name', sa.String(length=64), primary_key=True),
        sa.Column('model_version', sa.String(length=32), primary_key=True),
        sa.Column('model_type', sa.String(length=32), nullable=False),
        sa.Column('artifact_uri', sa.String(length=512), nullable=False),
        sa.Column('input_contract_version', sa.String(length=32), nullable=False),
        sa.Column('output_contract_version', sa.String(length=32), nullable=False),
        sa.Column('trained_on', sa.String(length=255), nullable=True),
        sa.Column('metrics', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # 11. Alerts
    op.create_table(
        'alerts',
        sa.Column('id', sa.String(length=64), primary_key=True),
        sa.Column('session_id', sa.String(length=64), sa.ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('defect_id', sa.String(length=64), sa.ForeignKey('defect_events.id', ondelete='CASCADE'), nullable=True),
        sa.Column('severity', sa.String(length=32), nullable=False),
        sa.Column('message', sa.String(length=255), nullable=False),
        sa.Column('acknowledged', sa.Boolean(), nullable=False),
        sa.Column('acknowledged_by', sa.String(length=128), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_alerts_session_id', 'alerts', ['session_id'])


def downgrade() -> None:
    op.drop_table('alerts')
    op.drop_table('model_registry')
    op.drop_table('calibration_artifacts')
    op.drop_table('media_assets')
    op.drop_table('ml_signals')
    op.drop_table('defect_events')
    op.drop_table('telemetry_samples')
    op.drop_table('track_segments')
    op.drop_table('sessions')
    op.drop_table('devices')
    op.drop_table('ingestion_keys')
