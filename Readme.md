# Sikili - Client and sales order sync with Odoo

Small FastAPI web app with HTML forms: create clients, list them, create a sale order per client. Each action syncs to Odoo over XML-RPC. PostgreSQL stores local rows plus `odoo_partner_id`, `odoo_order_id`, and sync status.

## Production (deployed)

| Service | URL |
| --- | --- |
| Web app (UI) | [https://sikili-webapp.emmanuelebeh.dev](https://sikili-webapp.emmanuelebeh.dev) (redirects to `/ui/clients`) |
| API / OpenAPI | [https://sikili-webapp.emmanuelebeh.dev/docs](https://sikili-webapp.emmanuelebeh.dev/docs) |
| Health check | [https://sikili-webapp.emmanuelebeh.dev/health](https://sikili-webapp.emmanuelebeh.dev/health) |
| Odoo (back office) | [https://sikili-odoo.emmanuelebeh.dev](https://sikili-odoo.emmanuelebeh.dev) |

Odoo database name: `sikili`. Use the credentials configured in Dokploy (`ODOO_LOGIN` / `ODOO_PASSWORD` for the web user; `ODOO_ADMIN_PASSWD` for the master password).

## How to run the project locally

### Option A - Docker (recommended)

Prerequisites: Docker with Compose v2.

```bash
git clone git@github.com:manuelebeh/sikili-tech-assigment-test.git
cd sikili-tech-assigment-test
cp .env.example .env
docker compose up
```

- First run: allow about 1 to 3 minutes. The Odoo container installs modules (`sale_management`, `account`) with HTTP disabled until bootstrap finishes, then starts the normal server.
- App: [http://localhost:8000](http://localhost:8000) (root redirects to `/ui/clients`).
- OpenAPI: [http://localhost:8000/docs](http://localhost:8000/docs).
- Reset everything: `docker compose down -v` (removes volumes `postgres_data` and `odoo_data`), then `docker compose up` again.

The `webapp` image runs `alembic upgrade head` before `uvicorn`, so the app database schema is applied automatically.

### Option B - Without Docker

Prerequisites: Python 3.12+, [uv](https://docs.astral.sh/uv/getting-started/installation/), PostgreSQL 16 reachable from your machine, Odoo 18 with Sales and Invoicing installed, same database name and credentials as in your `.env`.

1. Copy env: `cp .env.example .env` and set `ODOO_URL` (for example `http://localhost:8069`), `PGHOST` / `PGPORT` / `PGUSER` / `PGPASSWORD` / `PGDATABASE`, and `ODOO_LOGIN` / `ODOO_PASSWORD` to match your Odoo database user.
2. Install deps: `uv python install 3.12` then `uv sync`.
3. Migrations: `uv run alembic upgrade head`.
4. Run API: `uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`.

For a host-only Odoo config template (not used by Docker, which generates `/etc/odoo/odoo.conf` at startup), see `config/odoo.conf.example`.

## How to connect to your Odoo instance

When you use **Docker** with the provided `.env.example`:

| What | Value |
| --- | --- |
| Odoo URL in the browser | [http://localhost:8069](http://localhost:8069) |
| Database (db filter) | `sikili` (from `POSTGRES_DB`, default `sikili`) |
| Web user (back office) | Login `admin`, password `admin` (same as `ODOO_LOGIN` / `ODOO_PASSWORD` in `.env.example`) |
| Master password (database manager / restore) | Value of `ODOO_ADMIN_PASSWD` in `.env` (default `admin` in `.env.example`) |

The FastAPI container overrides `ODOO_URL` to `http://odoo:8069` on the Docker network. On the host, use `http://localhost:8069` in the browser.

If you **bring your own Odoo** instead of the compose stack: install the **Sales** and **Invoicing** apps, create or use a database whose name matches `PGDATABASE` / Odoo XML-RPC database name, set `ODOO_URL` and credentials in `.env`, and ensure the Sales app is available so `sale.order` creation works.

## Which Odoo objects we used and why

| Model | Role |
| --- | --- |
| `res.partner` | Represents the customer created from the web app. We set `customer_rank=1`, plus name, email, and optional phone. This is the standard Odoo customer record and is what Sales orders attach to. |
| `sale.order` | One quotation / sales order per local order. We set `partner_id` to the partner created for that client so the order is visible under the correct customer in Odoo. |
| `sale.order.line` | Created inline on the `sale.order` via the `order_line` x2many command. One line per app order: quantity `1`, `price_unit` from the app `amount`, and `name` from the app `product_name` so the free-text product label appears on the order. |
| `product.product` | Odoo requires a product on sale lines. We do not mirror your full catalog locally. The integration uses either `ODOO_DEFAULT_SALE_PRODUCT_ID` if set, or a single reusable service product (default code `SIKILI_MISC_LINE`) created or reused on first need, so each line still shows the human-readable product name in the line description. |

RPC transport: **XML-RPC** (`/xmlrpc/2/common`, `/xmlrpc/2/object`) implemented in `app/services/odoo_service.py` with the standard library only.

## Assumptions and simplifications

- **Single Odoo database** named like `POSTGRES_DB` / `PGDATABASE`; `dbfilter` in Docker locks Odoo to that database.
- **No local product catalog**: orders store `product_name` and `amount` in PostgreSQL; Odoo gets one generic `product.product` per line with the real label in the line `name`.
- **Sync status**: `odoo_sync_status` on clients and orders (`pending`, `synced`, `failed`). Failed Odoo calls are logged (structured error logging) and the UI/API returns an error message; the local row is kept with `failed` where applicable so nothing is silently dropped.
- **Order creation** requires the client to already have a synced partner (`odoo_partner_id` and `synced`); otherwise the app returns a clear validation error instead of creating an orphan order in Odoo.
- **Routes stay synchronous** (`def` handlers): FastAPI runs them in a worker thread pool so blocking XML-RPC does not stall the asyncio loop. Helpers such as `run_sync` exist for future async call sites.
- **Addons folder**: `docker-compose.yml` mounts `./addons` at `/mnt/extra-addons`. The repo ships an empty `addons/` (placeholder) so we can add custom modules without changing compose.

## What we would improve

- **Retries and idempotency**: bounded retries on transient Odoo/network errors; optional idempotency keys to avoid duplicate partners or orders on double submit.
- **Outbound webhooks or queue**: background worker (for example Celery or ARQ) so HTTP responses do not wait on Odoo latency; reconcile job for stuck `failed` rows.
- **Richer Odoo mapping**: optional mapping to real `product.product` records, taxes, pricelists, and company (`company_id`) for multi-company setups.
- **Tests**: integration tests against Odoo in CI (containerized) plus unit tests for the service layer with mocked XML-RPC.
- **Observability**: metrics and correlation ids on Odoo RPC spans; redacted logging review.

## Environment variables (reference)

Copy `.env.example` to `.env`. Important keys:

| Variable | Purpose |
| --- | --- |
| `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | PostgreSQL; shared by the `db` service, Odoo, and the app (via `PG*` in the webapp container). |
| `ODOO_ADDONS_PATH` | Odoo `addons_path` (Docker default includes `/mnt/extra-addons` and stock addons). |
| `ODOO_ADMIN_PASSWD` | Odoo master password (`admin_passwd` in `odoo.conf`). |
| `ODOO_INIT_MODULES` | Comma-separated modules installed on first Odoo boot (default `sale_management,account`). |
| `ODOO_LOGIN`, `ODOO_PASSWORD` | XML-RPC user for the FastAPI app (defaults `admin` / `admin` in `.env.example`). |
| `ODOO_URL` | Odoo base URL; overridden to `http://odoo:8069` for the `webapp` service in Compose. |
| `DATABASE_URL` | Optional; if unset, SQLAlchemy URL is built from `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`. |
| `ODOO_DEFAULT_SALE_PRODUCT_ID` | Optional; forces a specific `product.product` id for integration lines instead of auto lookup/create. |

## Troubleshooting

- **Stale volumes**: `docker compose down -v`, then `docker compose up`.
- **Long first boot**: Odoo module install dominates; healthcheck waits until port `8069` accepts connections, so `webapp` starts only after Odoo is up.
- **Bootstrap detail**: see comments and steps in `docker/odoo/docker-entrypoint.sh` (renders `odoo.conf`, waits for Postgres, creates DB if missing, runs `-i` with `--stop-after-init --no-http` when the Odoo schema is missing).
