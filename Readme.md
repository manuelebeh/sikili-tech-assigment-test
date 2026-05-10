# Sikili — FastAPI / PostgreSQL / Odoo stack

## Local development (via **uv**)

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/).
2. At the repository root:

```bash
uv python install 3.12    # once, if uv has no 3.12 available yet
uv sync                     # creates .venv/ and installs from uv.lock
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Add a dependency: `uv add <package>` (updates `pyproject.toml` and `uv.lock`).
- Do not commit `.venv/`; **do commit** `pyproject.toml` and `uv.lock`.

## Docker (Python comes from the image; no host 3.12 required)

```bash
cp .env.example .env   # then set secrets (see below)
docker compose up -d --build
```

The API listens on **8000**, Odoo on **8069** (+ **8072** for the gevent worker / real-time bus).

### Odoo: blank page after login, or login page without CSS

This is a known issue with Odoo + Docker (including macOS): `/odoo` or `/web` stays blank even though auth works.

1. **Ports**: **8069** and **8072** mappings must be active (`docker compose ps`). Generated config sets **`gevent_port = 8072`** (Odoo 18 — replaces deprecated `longpolling_port`).
2. **Single base URL**: stick to one host (**`127.0.0.1`** *or* **`localhost`**, not both). Optionally set **Settings → Technical → Parameters → System → `web.base.url`** to match.
3. **Asset caches**: from the repo root, pass your database name (e.g. `sikili_test_db`):

```bash
./docker/odoo/rebuild-web-assets.sh sikili_test_db
```

Then open **`http://127.0.0.1:8069/web/login?debug=assets`** and hard-refresh a few times.

4. **Browser**: prefer **Chrome or Firefox**; use **F12 → Console / Network** to inspect **`/web/assets/...`** (500s or blocked files).

5. **`Permission denied` on `/var/lib/odoo/filestore`** (see `docker compose logs odoo`): the filestore must belong to user **`odoo`**. `docker/odoo/docker-entrypoint.sh` runs **`chown -R odoo:odoo /var/lib/odoo`** on startup; after updating it, run **`docker compose up -d --force-recreate odoo`**. One-off fix:  
   `docker compose exec -u root odoo chown -R odoo:odoo /var/lib/odoo`

### Environment variables (no secrets in the repo)

Everything is read from **`.env`**: copy **`.env.example`**, then set at least **`POSTGRES_PASSWORD`**, **`ODOO_ADMIN_PASSWD`**, and **`ODOO_ADDONS_PATH`** (comma-separated list: mounted addons + official addons inside the image).

Under Docker, **`odoo.conf` is generated at startup** by `docker/odoo/docker-entrypoint.sh` from those variables (DB host/port/user/password, `addons_path`, `admin_passwd`). For Odoo **outside Docker**, use **`config/odoo.conf.example`** as a template for a local file.
