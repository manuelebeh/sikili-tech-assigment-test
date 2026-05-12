# Claude AI Session — Sikili Tech Assignment

**Tool:** Claude (Anthropic)  
**Context:** Technical interview assignment — FastAPI + PostgreSQL + Odoo 18 integration  
**Developer profile:** Experienced in Python and FastAPI, first project integrating Odoo  
**Date:** May 2026

---

## 1. Project Analysis & Roadmap

**Q: I have this technical test to complete for an interview. Analyse the README and give me a roadmap. I'm on Mac M.**

**A:**

After reading the brief, the stack I recommend is **FastAPI + PostgreSQL + Odoo 18 via XML-RPC**, with Alembic for migrations and Jinja2 for the UI.

**Why XML-RPC and not JSON-RPC?**  
JSON-RPC is the native protocol for Odoo's web client. However, for server-side Python integration, `xmlrpc.client` from the standard library is the right choice — zero third-party dependencies, and it's what all official Odoo documentation uses.

**On Mac M (arm64):** The official `odoo:18.0` Docker image is multi-arch (arm64 native). No Rosetta needed for Odoo itself.

**Roadmap (estimated 7–9h of effective code):**

- **Phase 0 (~30 min):** Docker Desktop setup, GitHub repo, project structure
- **Phase 1 (~1h):** `docker-compose.yml` with 3 services (db, odoo, webapp), `odoo.conf`, verify Odoo starts on :8069
- **Phase 2 (~45 min):** SQLAlchemy models (`clients`, `orders`), Alembic initial migration
- **Phase 3 (~2h):** `app/services/odoo_service.py` — isolated XML-RPC layer (`create_partner`, `create_sale_order`), error handling
- **Phase 4 (~1h30):** FastAPI routes + Jinja2 templates
- **Phase 5 (~45 min):** End-to-end testing + error case (Odoo down)
- **Phase 6 (~1h):** README, AI session export, optional deployment

---

## 2. Data Modelling — Why No `products` Table?

**Q: Why don't we have a products table? I think that's the ideal solution**

**A:**

The brief says: *"Create a sale order — product name (e.g. 'Samsung Galaxy A55'), total price."* The product is a free-text input, not a managed entity. There is no:

- product list to display
- catalogue to maintain
- product reuse across orders in the business sense

Adding a `products` table would mean an extra relation, extra CRUD routes, and an extra Odoo sync (`product.product` or `product.template`) — all to store a string that belongs directly on the order.

The brief also says explicitly: *"Do not over-engineer. We value clarity and working code over clever abstractions."*

So `product_name VARCHAR` + `amount NUMERIC` on `orders` is the correct decision here.

**What to note in the README under "assumptions":**  
*"Products are not modelled as a separate entity because the brief treats the product as a free-text input on the order. With more time, we would create a `product.product` catalogue on the Odoo side and a local `products` table to allow selection from a reference list."*

---

## 3. FastAPI Project Structure

**Q: Should we follow the zhanymkanov/fastapi-best-practices ? I usually just use a few ideas and best practices here, but for this project, that’s over-engineering, isn’t it?**

**A:**

Partly yes, partly no. This guide is excellent for a multi-year codebase. For a 6–10h test with 2 models and one external service, some parts apply perfectly, others are pure over-engineering.

**Adopt — low cost, strong signal:**

Domain-based structure (`clients/`, `orders/`) with `router.py` + `schemas.py` + `service.py` in each folder. This is exactly what the brief asks when it says *"Odoo calls isolated in a dedicated service layer"*.

`Pydantic BaseSettings` for config (`.env`) — mandatory. Never hardcode credentials.

**Ignore for this test:**

- Nested `src/` structure → unnecessary at this scale  
- `dependencies.py`, `constants.py`, `exceptions.py` per module → empty files that add noise  
- Async tests from day 0 → the brief doesn't mention tests  
- `ruff`, `logging.ini` → nice to have, not an evaluation criterion  

**The genuinely useful point from the guide:**

> *"If you must use sync SDK, then run it in a thread pool"*

`xmlrpc.client` is synchronous. If you use `async def` in your FastAPI routes, the RPC call will block the event loop. The clean solution:

```python
import asyncio
from functools import partial

async def create_partner(name, email, phone):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, partial(_sync_create_partner, name, email, phone)
    )
    return result
```

This is the kind of detail a Tech Lead is expected to know.

---

## 4. Final Project Structure

**Q: Given all the decisions above, what is the coherent final structure?**

**A:**

Since all order routes are nested under `/clients`, there is no need for a separate `orders/` module. The final structure:

```
app/
├── routers/
│   └── clients.py     # All routes: /clients + /clients/{id}/orders
├── models.py          # Client + Order SQLAlchemy models
├── schemas.py         # All Pydantic schemas
├── service.py         # Local CRUD
├── services/
│   └── odoo_service.py  # ← only isolation explicitly requested
├── database.py
├── config.py          # Pydantic BaseSettings
└── main.py
```

**README note:** *"Intentionally flat structure because the brief requires only one business domain. Only the Odoo service is isolated as explicitly requested."*

---

## 5. Odoo Module Selection

**Q: Do we need both Sales and Invoicing for this assignment?**

**A:**

The brief explicitly requests **Sales AND Invoicing**. However, in Odoo 18, `sale_management` depends on `account` (Invoicing) as a transitive dependency — so installing `sale_management` also installs Invoicing automatically.

This is correctly noted in the README: *"Invoicing is pulled in transitively as a dependency of Sales."*  
This is factually accurate and perfectly defensible in the interview.

---

## 6. Odoo Docker Auto-Install — What Actually Works

**Q: Can we use an environment variable like `ODOO_INSTALL_MODULES` in docker-compose to auto-install modules?**

**A:**

After research: **`ODOO_INSTALL_MODULES` is not a variable supported by the official `odoo:18.0` image.**

The official image only supports four environment variables for the PostgreSQL connection: `HOST`, `PORT`, `USER`, and `PASSWORD`. Nothing for module installation.

**What actually works:**

**Option 1 — via `odoo.conf`** (recommended):
```ini
[options]
init = sale_management
without_demo = all
```
The `init` parameter installs listed modules at **first boot only** when the DB is empty.

**Option 2 — custom `docker-entrypoint.sh`:**  
Write a shell script that:
1. Waits for PostgreSQL
2. Creates the DB if it doesn't exist
3. Runs `odoo -d $DB -i $MODULES --stop-after-init --no-http` on first boot
4. Then exec's the regular Odoo server

This is the most robust approach and gives full control over the bootstrap sequence.

---

## 7. Odoo XML-RPC — Key Concepts

**Q: How does Odoo XML-RPC authentication and object creation work?**

**A:**

Odoo exposes two XML-RPC endpoints:

- `/xmlrpc/2/common` — authentication, returns a `uid`
- `/xmlrpc/2/object` — all model operations (create, read, write, unlink)

**Authentication:**
```python
import xmlrpc.client

common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
uid = common.authenticate(DB, LOGIN, PASSWORD, {})
```

**Creating a partner (`res.partner`):**
```python
models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
partner_id = models.execute_kw(
    DB, uid, PASSWORD,
    'res.partner', 'create',
    [{'name': name, 'email': email, 'phone': phone, 'customer_rank': 1}]
)
```

**Creating a sale order (`sale.order`) with an order line:**
```python
order_id = models.execute_kw(
    DB, uid, PASSWORD,
    'sale.order', 'create',
    [{'partner_id': partner_id, 'order_line': [(0, 0, {
        'name': product_name,
        'price_unit': amount,
        'product_uom_qty': 1,
    })]}]
)
```

**Key Odoo objects used:**
- `res.partner` with `customer_rank=1` — universal Odoo model for any contact/customer
- `sale.order` linked to `partner_id` — standard sales order, visible in Sales → Orders
- `sale.order.line` — each product line is a separate entry, mandatory for a valid order

**Important:** `(0, 0, {...})` is Odoo's Many2many/One2many write command syntax. `0` means "create a new record linked to this order."

---

## 8. Error Handling Strategy

**Q: How should we handle Odoo being unavailable?**

**A:**

The pattern: try the Odoo call, catch the exception, update `odoo_sync_status = "failed"` in the local DB, log the error, and return a readable message to the user. The local record is always saved first — Odoo sync is a best-effort operation on top.

```python
try:
    partner_id = odoo_service.create_partner(name, email, phone)
    db_client.odoo_partner_id = partner_id
    db_client.odoo_sync_status = "synced"
except Exception as e:
    logger.error(f"Odoo sync failed for client {db_client.id}: {e}")
    db_client.odoo_sync_status = "failed"
finally:
    db.commit()
```

This way, if Odoo is down, the app keeps working — the client is saved locally and can be re-synced later.

---

*Session generated with Claude (Anthropic) — claude-sonnet-4-6*
