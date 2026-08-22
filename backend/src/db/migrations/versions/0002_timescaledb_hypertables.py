"""TimescaleDB hypertables partitioning migration

Revision ID: 0002_timescaledb_hypertables
Revises: 0001_initial_schema
Create Date: 2026-08-21 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0002_timescaledb_hypertables'
down_revision = '0001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if running against a PostgreSQL database with TimescaleDB
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    if dialect_name == "postgresql":
        try:
            # Check if timescaledb extension is available on the server (handles RDS which lacks it)
            result = bind.execute(sa.text("SELECT 1 FROM pg_available_extensions WHERE name = 'timescaledb'"))
            is_available = result.scalar() is not None
            
            if is_available:
                # Enable TimescaleDB extension if not already enabled
                op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
                
                # Convert telemetry_samples and ml_signals to TimescaleDB hypertables partitioned by 1 day
                op.execute("SELECT create_hypertable('telemetry_samples', 'timestamp', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE);")
                op.execute("SELECT create_hypertable('ml_signals', 'timestamp', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE);")
            else:
                print("[WARN] TimescaleDB extension not available on this PostgreSQL server (e.g. RDS). Skipping hypertable creation.")
        except Exception as exc:
            print(f"[WARN] TimescaleDB hypertable creation skipped or unsupported: {exc}")


def downgrade() -> None:
    pass
