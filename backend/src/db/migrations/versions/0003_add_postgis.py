"""Add PostGIS extension and spatial indexing

Revision ID: 0003_add_postgis
Revises: 0002_timescaledb_hypertables
Create Date: 2026-08-21 02:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0003_add_postgis'
down_revision = '0002_timescaledb_hypertables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    if dialect_name == "postgresql":
        try:
            # Enable PostGIS extension
            op.execute("CREATE EXTENSION IF NOT EXISTS postgis CASCADE;")
            # Create compound spatial B-tree index on lat/lon
            op.execute("CREATE INDEX IF NOT EXISTS idx_defect_events_lat_lon ON defect_events (latitude, longitude);")
            op.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_lat_lon ON telemetry_samples (latitude, longitude);")
        except Exception as exc:
            print(f"[WARN] PostGIS migration skipped or unsupported: {exc}")


def downgrade() -> None:
    pass
