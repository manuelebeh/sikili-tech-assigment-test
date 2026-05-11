#!/usr/bin/env bash
set -euo pipefail
if [[ -n "${1:-}" ]]; then
  DB="$1"
elif DB="$(docker compose exec -T webapp printenv PGDATABASE 2>/dev/null | tr -d '\r\n')" && [[ -n "$DB" ]]; then
  :
else
  DB="${POSTGRES_DB:-sikili}"
fi
echo "Odoo database: ${DB}"

echo "Clearing asset caches inside the odoo container..."
docker compose exec -u root odoo bash -c '
  set -e
  for base in /var/lib/odoo/.local/share/Odoo /var/lib/odoo; do
    if [[ -d "${base}/web/assets" ]]; then rm -rf "${base}/web/assets"/*; fi
  done
  echo "OK: asset caches cleared (if present)."
'

echo "Fixing filestore ownership..."
docker compose exec -u root odoo chown -R odoo:odoo /var/lib/odoo

echo "Upgrading module web (assets rebuilt on next load)..."
docker compose exec -u odoo odoo odoo -d "${DB}" -u web --stop-after-init

docker compose exec -u root odoo chown -R odoo:odoo /var/lib/odoo

echo
echo "Next: http://127.0.0.1:8069/web/login?debug=assets — hard-refresh (Chrome/Firefox if needed)."
