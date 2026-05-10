# Sikili — stack FastAPI / PostgreSQL / Odoo

## Développement local (tout passe par **uv**)

1. Installer [uv](https://docs.astral.sh/uv/getting-started/installation/).
2. À la racine du dépôt :

```bash
uv python install 3.12    # une fois si aucune 3.12 dispo pour uv
uv sync                     # crée .venv/ et installe depuis uv.lock
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Ajouter une dépendance : `uv add <nom-du-paquet>` (met à jour `pyproject.toml` et `uv.lock`).
- Ne pas commiter `.venv/` ; **commiter** `pyproject.toml` et `uv.lock`.

## Docker (Python fourni par l’image, pas besoin de 3.12 sur l’hôte)

```bash
cp .env.example .env   # puis renseigner les secrets (voir ci-dessous)
docker compose up -d --build
```

L’API est exposée sur le port **8000**, Odoo sur **8069**.

### Variables d’environnement (aucune valeur sensible dans le dépôt)

Tout est lu depuis **`.env`** : copier **`.env.example`**, puis définir au minimum **`POSTGRES_PASSWORD`**, **`ODOO_ADMIN_PASSWD`**, et **`ODOO_ADDONS_PATH`** (liste séparée par des virgules : addons montés + addons officiels dans l’image).

Sous Docker, **`odoo.conf` est généré au démarrage** par `docker/odoo/docker-entrypoint.sh` à partir de ces variables (hôte / port / user / mot de passe DB, `addons_path`, `admin_passwd`). Pour une installation Odoo **hors Docker**, t’inspirer de **`config/odoo.conf.example`** (fichier local non versionné si tu préfères).
