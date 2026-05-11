# Sikili — FastAPI / PostgreSQL / Odoo stack

## Quickstart (Docker)

One command, zero manual setup. The stack starts PostgreSQL, Odoo 18 and the FastAPI app, and bootstraps the Odoo database with the **Sales** and **Contacts** modules on first boot (Invoicing is pulled in transitively as a dependency of Sales).

```bash
git clone <repo>
cd sikili-tech-assigment-test
cp .env.example .env
docker compose up
```

1. Wait ~2 minutes on the very first run: Odoo creates the database `sikili` and installs `sale_management` + `contacts` (Invoicing comes along as a dependency of Sales). The HTTP port stays closed until the bootstrap is done — that is intentional.
2. Open **http://localhost:8069** — Odoo login: `admin` / `admin`.
3. Open **http://localhost:8000** — FastAPI app (and **http://localhost:8000/docs** for the OpenAPI UI).

Subsequent `docker compose up` runs reuse the existing database and skip the bootstrap step. Use `docker compose down -v` to fully reset (drops the volumes and forces a fresh install).

### What the bootstrap does

On first boot, `docker/odoo/docker-entrypoint.sh`:

- Renders `/etc/odoo/odoo.conf` from the `.env` variables (`db_name`, `dbfilter`, `list_db = False`, `without_demo = all`).
- Waits for PostgreSQL.
- Creates the `POSTGRES_DB` database if it doesn't exist.
- If the Odoo schema isn't initialized yet, runs `odoo -d $POSTGRES_DB -i $ODOO_INIT_MODULES --without-demo=all --stop-after-init --no-http` (default modules: `sale_management,contacts`).
- Then exec's the regular Odoo server.

To customize, edit `ODOO_INIT_MODULES` in `.env` before the first `docker compose up`.

## Local development (no Docker)

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/).
2. At the repository root:

```bash
uv python install 3.12
uv sync
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Add a dependency: `uv add <package>`.
- Do not commit `.venv/`; commit `pyproject.toml` and `uv.lock`.
- Run Alembic migrations: `uv run alembic upgrade head`.
- A host-only `odoo.conf` template is provided at `config/odoo.conf.example`.

## Environment

Copy `.env.example` to `.env`. The provided defaults are sufficient to run the stack as a reviewer. The relevant variables:

| Variable | Purpose |
| --- | --- |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Shared by PostgreSQL, the FastAPI app and Odoo. |
| `ODOO_ADMIN_PASSWD` | Master password for Odoo DB management. |
| `ODOO_INIT_MODULES` | Comma-separated list of Odoo modules installed on first boot. Defaults to `sale_management,contacts`. |
| `ODOO_LOGIN`, `ODOO_PASSWORD` | Credentials the FastAPI app uses to talk to Odoo via XML-RPC. Defaults to `admin` / `admin`. |
| `ODOO_URL` | Base URL of Odoo. Overridden to `http://odoo:8069` inside Docker. |

## Schema notes

- No `products` table: orders store `product_name` and `amount` as free text (no local catalog). A richer design could mirror Odoo products later.
- Odoo XML-RPC is synchronous; see `app/services/odoo_service.py` and wrap blocking calls from async code with `run_in_executor` when needed.

## Troubleshooting

- **Odoo login page is unstyled** — the filestore ownership drifted (usually after a manual `docker compose exec` as root). Rebuild assets:

  ```bash
  ./docker/odoo/rebuild-web-assets.sh
  ```

  Then hit **http://127.0.0.1:8069/web/login?debug=assets** and hard-refresh.

- **`docker compose up` exits because the DB volume is stale** — `docker compose down -v` to wipe `postgres_data` and `odoo_data`, then start again.

- **Long first boot** — Odoo bootstrap is the longest step (~2 min). The Odoo container only marks itself healthy once port 8069 is open, so the FastAPI service waits for it.

## Database

`PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE` or `DATABASE_URL` — see `.env.example`. The Docker `webapp` service runs `alembic upgrade head` before `uvicorn`.
