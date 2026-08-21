#!/usr/bin/env bash
# =============================================================================
# TrackChain Database Bootstrap Script (PostgreSQL / TimescaleDB)
# Idempotent database & role initialization for TrackChain real-mode operation.
# =============================================================================

set -e

DB_USER="trackchain"
DB_PASS="trackchain_secret"
DB_NAME="trackchain_db"

echo "[INFO] Initializing TrackChain Database: user='${DB_USER}', db='${DB_NAME}'..."

# Detect appropriate psql connection command
if psql -U postgres -d postgres -c '\q' 2>/dev/null; then
    PSQL_ADMIN="psql -U postgres -d postgres"
elif psql -d postgres -c '\q' 2>/dev/null; then
    PSQL_ADMIN="psql -d postgres"
elif psql -U "$(whoami)" -d postgres -c '\q' 2>/dev/null; then
    PSQL_ADMIN="psql -U $(whoami) -d postgres"
elif psql -d template1 -c '\q' 2>/dev/null; then
    PSQL_ADMIN="psql -d template1"
else
    PSQL_ADMIN="psql"
fi

echo "[INFO] Using admin connection command: ${PSQL_ADMIN}"

# 1. Create role if not exists
ROLE_EXISTS=$(${PSQL_ADMIN} -tc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | tr -d '[:space:]')
if [ "${ROLE_EXISTS}" = "1" ]; then
    echo "[OK] Role '${DB_USER}' already exists."
    ${PSQL_ADMIN} -c "ALTER USER ${DB_USER} WITH PASSWORD '${DB_PASS}';" >/dev/null 2>&1 || true
else
    echo "[INFO] Creating role '${DB_USER}'..."
    ${PSQL_ADMIN} -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASS}' CREATEDB;"
    echo "[OK] Role '${DB_USER}' created successfully."
fi

# 2. Create database if not exists
DB_EXISTS=$(${PSQL_ADMIN} -tc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | tr -d '[:space:]')
if [ "${DB_EXISTS}" = "1" ]; then
    echo "[OK] Database '${DB_NAME}' already exists."
else
    echo "[INFO] Creating database '${DB_NAME}' with owner '${DB_USER}'..."
    ${PSQL_ADMIN} -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"
    echo "[OK] Database '${DB_NAME}' created successfully."
fi

# 3. Grant privileges
echo "[INFO] Granting permissions on '${DB_NAME}' to '${DB_USER}'..."
${PSQL_ADMIN} -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};" >/dev/null 2>&1 || true
${PSQL_ADMIN} -c "ALTER DATABASE ${DB_NAME} OWNER TO ${DB_USER};" >/dev/null 2>&1 || true

# Grant schema public permissions on the target database
if psql -U "${DB_USER}" -d "${DB_NAME}" -c '\q' 2>/dev/null; then
    psql -U "${DB_USER}" -d "${DB_NAME}" -c "GRANT ALL ON SCHEMA public TO ${DB_USER};" >/dev/null 2>&1 || true
fi

echo "[SUCCESS] TrackChain PostgreSQL database bootstrap complete!"
