#!/bin/bash
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

exec runuser -u odoo -- /entrypoint.sh "$@"
