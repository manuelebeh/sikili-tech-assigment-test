# Sikili — FastAPI / PostgreSQL / Odoo stack

## Local development (uv)

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/).
2. At the repository root:

```bash
uv python install 3.12
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Add a dependency: `uv add <package>`.
- Do not commit `.venv/`; commit `pyproject.toml` and `uv.lock`.

## Docker

```bash
cp .env.example .env
docker compose up -d --build
```

API on **8000**, Odoo on **8069** (and **8072** for gevent / longpolling).

### Odoo: blank page or unstyled login

Common with Odoo in Docker (including macOS).

1. Ensure **8069** and **8072** are mapped (`docker compose ps`). Odoo 18 uses **`gevent_port = 8072`**.
2. Use one host consistently (**`127.0.0.1`** or **`localhost`**). Optionally set **`web.base.url`** in Odoo to match.
3. Rebuild assets (replace with your database name):

```bash
./docker/odoo/rebuild-web-assets.sh sikili_test_db
```

Then open **`http://127.0.0.1:8069/web/login?debug=assets`** and hard-refresh.

4. Prefer Chrome or Firefox; check DevTools for **`/web/assets/...`** errors.

5. **`Permission denied` on `/var/lib/odoo/filestore`**: filestore must be owned by **`odoo`**. The entrypoint runs **`chown -R odoo:odoo /var/lib/odoo`**; after changes run **`docker compose up -d --force-recreate odoo`**, or once: **`docker compose exec -u root odoo chown -R odoo:odoo /var/lib/odoo`**.

### Environment

Copy **`.env.example`** to **`.env`** and set secrets. Required for Compose: **`POSTGRES_PASSWORD`**, **`ODOO_ADMIN_PASSWD`**, **`ODOO_ADDONS_PATH`**. For the FastAPI app to call Odoo XML-RPC, also set **`ODOO_DATABASE`**, **`ODOO_LOGIN`**, **`ODOO_PASSWORD`** (Odoo user password, not the master password).

With Docker, **`odoo.conf`** is generated at startup from **`docker/odoo/docker-entrypoint.sh`**. For a non-Docker Odoo, start from **`config/odoo.conf.example`**.

## Schema notes

- No **`products`** table: orders store **`product_name`** and **`amount`** as free text (no local catalog). A richer design could mirror Odoo products later.

- Odoo XML-RPC is synchronous; see **`app/services/odoo_service.py`** and wrap blocking calls from async code with **`run_in_executor`** when needed.

## Database

- **`PGHOST`**, **`PGPORT`**, **`PGUSER`**, **`PGPASSWORD`**, **`PGDATABASE`**, or **`DATABASE_URL`** — see **`.env.example`**.
- Migrations: **`uv run alembic upgrade head`** from the repo root. The Docker **`webapp`** service runs migrations before **`uvicorn`**.
