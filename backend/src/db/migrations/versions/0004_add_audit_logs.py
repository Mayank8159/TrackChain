"""Add audit_logs table for railway safety and compliance

Revision ID: 0004_add_audit_logs
Revises: 0003_add_postgis
Create Date: 2026-08-21 03:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0004_add_audit_logs'
down_revision = '0003_add_postgis'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('actor_type', sa.String(length=32), nullable=False),
        sa.Column('actor_id', sa.String(length=64), nullable=False),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('resource_type', sa.String(length=64), nullable=True),
        sa.Column('resource_id', sa.String(length=64), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=256), nullable=True),
    )

    op.create_index('ix_audit_timestamp', 'audit_logs', ['timestamp'])
    op.create_index('ix_audit_actor', 'audit_logs', ['actor_type', 'actor_id'])
    op.create_index('ix_audit_action', 'audit_logs', ['action'])


def downgrade() -> None:
    op.drop_index('ix_audit_action', table_name='audit_logs')
    op.drop_index('ix_audit_actor', table_name='audit_logs')
    op.drop_index('ix_audit_timestamp', table_name='audit_logs')
    op.drop_table('audit_logs')
