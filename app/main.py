"""Entry point for FastAPI — skeleton for docker compose (healthcheck)."""

from fastapi import FastAPI

app = FastAPI(title="Sikili API")


@app.get("/health")
def health():
    return {"status": "ok"}
