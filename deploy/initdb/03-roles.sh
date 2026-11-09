#!/bin/bash
# Sets the read-only chatbot role's password from the environment (schema.sql creates the role).
set -euo pipefail
psql -v ON_ERROR_STOP=1 -v pw="${CHATBOT_RO_PASSWORD:-change-me}" \
     --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'EOSQL'
ALTER ROLE chatbot_ro PASSWORD :'pw';
EOSQL
