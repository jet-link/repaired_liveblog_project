#!/bin/bash
# Run ONCE on the server (needs sudo): sudo bash fix_postgres_permissions.sh
set -euo pipefail
DB_NAME="brainstorm_db"
DB_USER="brainstorm_user"

sudo -u postgres psql -v ON_ERROR_STOP=1 <<SQL
ALTER DATABASE ${DB_NAME} OWNER TO ${DB_USER};
\\c ${DB_NAME}
GRANT ALL ON SCHEMA public TO ${DB_USER};
GRANT CREATE ON SCHEMA public TO ${DB_USER};
SQL
echo "PostgreSQL permissions updated for ${DB_USER} on ${DB_NAME}."
