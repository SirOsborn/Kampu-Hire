from __future__ import annotations
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routers.web import router as web_router

app = FastAPI(title="Kampu-Hire")
app.include_router(web_router)

# If you add custom CSS/JS later
app.mount("/static", StaticFiles(directory="app/static"), name="static")
