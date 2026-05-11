"""FastAPI entrypoint: healthcheck, routers, lifespan."""

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.clients.router import router as clients_router
from app.web.router import router as ui_router

app = FastAPI(title="Sikili API")
app.include_router(clients_router)
app.include_router(ui_router)


@app.get("/")
def root():
    return RedirectResponse(url="/ui/clients", status_code=302)


@app.get("/health")
def health():
    return {"status": "ok"}
