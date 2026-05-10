#!/bin/bash
# Generate odoo.conf from environment (no secrets in the repo nor in the YAML compose).
# Run as root to write /etc/odoo/odoo.conf then delegate to the official entrypoint as user odoo.

set -euo pipefail

: "${POSTGRES_HOST:?POSTGRES_HOST is required}"
: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
: "${ODOO_ADMIN_PASSWD:?ODOO_ADMIN_PASSWD is required}"
: "${ODOO_ADDONS_PATH:?ODOO_ADDONS_PATH is required}"

POSTGRES_PORT="${POSTGRES_PORT:-5432}"
CONF="${ODOO_RC:-/etc/odoo/odoo.conf}"

mkdir -p "$(dirname "$CONF")"
umask 077
cat >"$CONF" <<EOF
[options]
addons_path = ${ODOO_ADDONS_PATH}
admin_passwd = ${ODOO_ADMIN_PASSWD}
data_dir = /var/lib/odoo
db_host = ${POSTGRES_HOST}
db_port = ${POSTGRES_PORT}
db_user = ${POSTGRES_USER}
db_password = ${POSTGRES_PASSWORD}
EOF

chown odoo:odoo "$CONF"
chmod 640 "$CONF"

exec runuser -u odoo -- /entrypoint.sh "$@"
