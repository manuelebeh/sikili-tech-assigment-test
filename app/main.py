"""FastAPI entrypoint: healthcheck, routers, lifespan."""

from fastapi import FastAPI

from app.clients.router import router as clients_router
from app.orders.router import router as orders_router

app = FastAPI(title="Sikili API")
app.include_router(clients_router)
app.include_router(orders_router)


@app.get("/health")
def health():
    return {"status": "ok"}
