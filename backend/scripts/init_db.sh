#!/usr/bin/env bash
set -euo pipefail

# --- Colors & Logging ---
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${BLUE}[INFO]${NC}  $1"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
header(){ echo -e "\n${CYAN}═══════════════════════════════════════════════════${NC}"; echo -e "${CYAN}  $1${NC}"; echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"; }

header "TrackChain Database Bootstrap (PostgreSQL / TimescaleDB)"

DB_USER="${DB_USER:-trackchain}"
DB_PASS="${DB_PASS:-trackchain_secret}"
DB_NAME="${DB_NAME:-trackchain_db}"

info "Target Database: user='${DB_USER}', db='${DB_NAME}'"

if psql -U postgres -d postgres -c '\q' 2>/dev/null; then
    PSQL_ADMIN="psql -U postgres -d postgres"
elif psql -d postgres -c '\q' 2>/dev/null; then
    PSQL_ADMIN="psql -d postgres"
elif psql -U "$(whoami)" -d postgres -c '\q' 2>/dev/null; then
    PSQL_ADMIN="psql -U $(whoami) -d postgres"
else
    PSQL_ADMIN="psql"
fi

info "Using admin command: ${PSQL_ADMIN}"

# 1. Create role if not exists
ROLE_EXISTS=$(${PSQL_ADMIN} -tc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" 2>/dev/null | tr -d '[:space:]' || true)
if [ "${ROLE_EXISTS}" = "1" ]; then
    ok "Role '${DB_USER}' already exists"
    ${PSQL_ADMIN} -c "ALTER USER ${DB_USER} WITH PASSWORD '${DB_PASS}';" >/dev/null 2>&1 || true
else
    info "Creating role '${DB_USER}'..."
    ${PSQL_ADMIN} -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASS}' CREATEDB;"
    ok "Role '${DB_USER}' created"
fi

# 2. Create database if not exists
DB_EXISTS=$(${PSQL_ADMIN} -tc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" 2>/dev/null | tr -d '[:space:]' || true)
if [ "${DB_EXISTS}" = "1" ]; then
    ok "Database '${DB_NAME}' already exists"
else
    info "Creating database '${DB_NAME}'..."
    ${PSQL_ADMIN} -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"
    ok "Database '${DB_NAME}' created"
fi

# 3. Grant privileges
info "Granting privileges on '${DB_NAME}'..."
${PSQL_ADMIN} -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};" >/dev/null 2>&1 || true
${PSQL_ADMIN} -c "ALTER DATABASE ${DB_NAME} OWNER TO ${DB_USER};" >/dev/null 2>&1 || true

header "Database Bootstrap Complete"
