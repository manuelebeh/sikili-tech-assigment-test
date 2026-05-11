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

1. Ensure **8069** and **8072** are mapped (`docker compose ps`). Odoo 18 uses **`gevent_port = 8072`**.
2. Use one host consistently (**`127.0.0.1`** or **`localhost`**). If asset URLs point at an internal host, set **`web.base.url`** in Odoo (**Settings → Technical → Parameters → System Parameters**).
3. Rebuild assets (optional DB name; otherwise uses the webapp’s **`PGDATABASE`**):

```bash
./docker/odoo/rebuild-web-assets.sh
```

Then open **`http://127.0.0.1:8069/web/login?debug=assets`** (or your host) and hard-refresh.

4. Prefer Chrome or Firefox; check DevTools for **`/web/assets/...`** errors.

5. **`500` on `/web/assets/...`** with **`PermissionError: ... filestore/...`** in logs: the filestore was written as **root**. Run **`docker compose exec -u root odoo chown -R odoo:odoo /var/lib/odoo`**, then refresh. **`./docker/odoo/rebuild-web-assets.sh`** runs **`chown`** and **`odoo -u web`** as **`odoo`** to avoid that. The image entrypoint also **`chown`**s **`/var/lib/odoo`** on start; use **`docker compose up -d --force-recreate odoo`** if permissions drift.

### Environment

Copy **`.env.example`** to **`.env`** and set secrets. Compose requires **`POSTGRES_PASSWORD`**, **`ODOO_ADMIN_PASSWD`**, **`ODOO_ADDONS_PATH`**. For XML-RPC from the API: **`ODOO_LOGIN`**, **`ODOO_PASSWORD`**.

**Databases:** use one PostgreSQL database name: **`POSTGRES_DB`** (Compose sets **`PGDATABASE`** for the API and Odoo XML-RPC). Avoid the catalog name **`postgres`** for that app DB (Odoo hides it in the selector; use e.g. **`sikili`**).

If you used **`POSTGRES_DB=postgres`** before, pick a new name (e.g. **`sikili`**), **`docker compose down -v`**, **`up -d --build`**, then init Odoo on that DB (UI or **`docker compose exec odoo odoo -d sikili -i base --stop-after-init`**).

**Odoo “default” data:** the generated **`odoo.conf`** always sets **`without_demo = all`** (no demo XML). You still get **required** master data (company, localization, journals/taxes from the country you pick). When creating a database **in the browser**, leave **“Load demonstration data”** unchecked. Host-only Odoo: **`config/odoo.conf.example`**.

## Schema notes

- No **`products`** table: orders store **`product_name`** and **`amount`** as free text (no local catalog). A richer design could mirror Odoo products later.

- Odoo XML-RPC is synchronous; see **`app/services/odoo_service.py`** and wrap blocking calls from async code with **`run_in_executor`** when needed.

## Database

- **`PGHOST`**, **`PGPORT`**, **`PGUSER`**, **`PGPASSWORD`**, **`PGDATABASE`**, or **`DATABASE_URL`** — see **`.env.example`**.
- Migrations: **`uv run alembic upgrade head`** from the repo root. The Docker **`webapp`** service runs migrations before **`uvicorn`**.
