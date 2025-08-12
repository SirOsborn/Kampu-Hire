from __future__ import annotations
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routers.web import router as web_router
from app.routers.screening import router as screening_router
from app.routers.screening import warmup_model

app = FastAPI(title="Kampu-Hire")
app.include_router(web_router)
app.include_router(screening_router)

# If you add custom CSS/JS later
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.on_event("startup")
async def _startup_warmup():
	# Preload and warm the transformer to reduce first-request latency
	try:
		warmup_model()
	except Exception as e:
		print(f"[main] warmup failed: {e}")
