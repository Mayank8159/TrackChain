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


def downgrade() -> None:
    op.drop_table('sessions')
    op.drop_table('devices')
    op.drop_table('ingestion_keys')
