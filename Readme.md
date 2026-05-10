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
cp .env.example .env   # puis renseigner POSTGRES_PASSWORD
docker compose up -d --build
```

L’API est exposée sur le port **8000**, Odoo sur **8069**.
