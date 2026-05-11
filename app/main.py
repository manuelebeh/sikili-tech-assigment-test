"""FastAPI entrypoint: healthcheck, routers, lifespan."""

from fastapi import FastAPI

from app.clients.router import router as clients_router

app = FastAPI(title="Sikili API")
app.include_router(clients_router)


@app.get("/health")
def health():
    return {"status": "ok"}
