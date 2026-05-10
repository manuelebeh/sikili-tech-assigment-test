#!/bin/bash
# Generate odoo.conf from environment (no secrets in the repo).
# Use Python to write the INI: passwords can contain $, #, etc.

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

export CONF
python3 <<'PY'
import os
import configparser
from pathlib import Path

# RawConfigParser: no `%` interpolation (passwords with % or $ stay literal for Odoo).
conf_path = Path(os.environ["CONF"])
opts = {
    "addons_path": os.environ["ODOO_ADDONS_PATH"],
    "admin_passwd": os.environ["ODOO_ADMIN_PASSWD"],
    "data_dir": "/var/lib/odoo",
    "db_host": os.environ["POSTGRES_HOST"],
    "db_port": os.environ.get("POSTGRES_PORT", "5432"),
    "db_user": os.environ["POSTGRES_USER"],
    "db_password": os.environ["POSTGRES_PASSWORD"],
    "http_interface": "0.0.0.0",
    "http_port": "8069",
    # Odoo 16+: gevent (real-time / bus); longpolling_port is deprecated in favor of gevent_port.
    "gevent_port": "8072",
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

# Volume odoo_data -> /var/lib/odoo must be writable by the Odoo process.
# Otherwise bundle generation for `/web/assets/*` hits PermissionError under .../filestore/... -> HTTP 500.
mkdir -p /var/lib/odoo
chown -R odoo:odoo /var/lib/odoo

exec runuser -u odoo -- /entrypoint.sh "$@"
