from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routers.web import router as web_router

app = FastAPI(title="Kampu-Hire HR Platform")
app.include_router(web_router)

# Mount static files for CSS/JS
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "kampu-hire"}