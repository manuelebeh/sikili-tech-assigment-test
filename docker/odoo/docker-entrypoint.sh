#!/bin/bash
set -euo pipefail

: "${POSTGRES_HOST:?POSTGRES_HOST is required}"
: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${ODOO_ADMIN_PASSWD:?ODOO_ADMIN_PASSWD is required}"
: "${ODOO_ADDONS_PATH:?ODOO_ADDONS_PATH is required}"

POSTGRES_PORT="${POSTGRES_PORT:-5432}"
ODOO_INIT_MODULES="${ODOO_INIT_MODULES:-sale_management,account}"
CONF="${ODOO_RC:-/etc/odoo/odoo.conf}"

mkdir -p "$(dirname "$CONF")"
umask 077

export CONF
python3 <<'PY'
import os
import configparser
from pathlib import Path

conf_path = Path(os.environ["CONF"])
db_name = os.environ["POSTGRES_DB"]
opts = {
    "addons_path": os.environ["ODOO_ADDONS_PATH"],
    "admin_passwd": os.environ["ODOO_ADMIN_PASSWD"],
    "data_dir": "/var/lib/odoo",
    "db_host": os.environ["POSTGRES_HOST"],
    "db_port": os.environ.get("POSTGRES_PORT", "5432"),
    "db_user": os.environ["POSTGRES_USER"],
    "db_password": os.environ["POSTGRES_PASSWORD"],
    "db_name": db_name,
    "dbfilter": f"^{db_name}$",
    "list_db": "False",
    "http_interface": "0.0.0.0",
    "http_port": "8069",
    "gevent_port": "8072",
    "without_demo": "all",
}
cfg = configparser.RawConfigParser()
cfg.add_section("options")
for key, val in opts.items():
    cfg.set("options", key, val)
with conf_path.open("w", encoding="utf-8") as f:
    cfg.write(f)
PY

chown odoo:odoo "$CONF"
chmod 640 "$CONF"

mkdir -p /var/lib/odoo
chown -R odoo:odoo /var/lib/odoo

export PGPASSWORD="$POSTGRES_PASSWORD"

echo "[entrypoint] Waiting for PostgreSQL at ${POSTGRES_HOST}:${POSTGRES_PORT}..."
for _ in $(seq 1 60); do
  if psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" \
      -d postgres -tAc 'SELECT 1' >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if ! psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" \
    -d postgres -tAc 'SELECT 1' >/dev/null 2>&1; then
  echo "[entrypoint] PostgreSQL did not become reachable in time." >&2
  exit 1
fi

DB_EXISTS="$(psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" \
  -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='${POSTGRES_DB}'" 2>/dev/null || true)"

if [ -z "${DB_EXISTS}" ]; then
  echo "[entrypoint] Creating PostgreSQL database '${POSTGRES_DB}'..."
  createdb -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" \
    -O "$POSTGRES_USER" -E UTF8 -T template0 "$POSTGRES_DB"
fi

SCHEMA_READY="$(psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" -tAc \
  "SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='ir_module_module'" \
  2>/dev/null || true)"

unset PGPASSWORD

if [ -z "${SCHEMA_READY}" ]; then
  echo "[entrypoint] First boot: initializing Odoo with modules: ${ODOO_INIT_MODULES}"
  echo "[entrypoint] This may take 1-3 minutes; the HTTP port stays closed until done."
  runuser -u odoo -- /entrypoint.sh odoo \
    -d "$POSTGRES_DB" \
    -i "$ODOO_INIT_MODULES" \
    --without-demo=all \
    --stop-after-init \
    --no-http
  echo "[entrypoint] Odoo bootstrap complete."
fi

exec runuser -u odoo -- /entrypoint.sh "$@"
