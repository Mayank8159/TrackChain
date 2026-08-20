# How to create and apply schema migrations.

# TrackChain Database Migrations

Alembic handles database schema evolution and TimescaleDB hypertable setups.

## Creating a new migration

```bash
# Generate auto-migration from SQLAlchemy models
alembic revision --autogenerate -m "Add new field or table"
```

## Applying migrations

```bash
# Upgrade to latest revision
alembic upgrade head

# Downgrade by one revision
alembic downgrade -1
```
