#!/usr/bin/env bash
# Rebuild Odoo CSS/JS bundles when the UI is blank or unstyled (common with Docker/macOS).
# See GitHub odoo/odoo #194073 and Odoo forums for /web/assets 500 errors.

set -euo pipefail
DB="${1:-${POSTGRES_DB:-postgres}}"
echo "Odoo database: ${DB}"

echo "Clearing asset caches inside the odoo container..."
docker compose exec -u root odoo bash -c '
  set -e
  # Paths vary by Odoo version / DATA_DIR
  for base in /var/lib/odoo/.local/share/Odoo /var/lib/odoo; do
    if [[ -d "${base}/web/assets" ]]; then rm -rf "${base}/web/assets"/*; fi
  done
  echo "OK: asset caches cleared (if present)."
'

echo "Upgrading module web (assets rebuilt on next load)..."
docker compose exec odoo odoo -d "${DB}" -u web --stop-after-init

echo
echo "Next: open http://127.0.0.1:8069/web/login?debug=assets"
echo "Hard-refresh 2–3 times if needed. Use Chrome or Firefox if Safari misbehaves."
