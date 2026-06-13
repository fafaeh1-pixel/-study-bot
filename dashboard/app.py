from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from dashboard.routes import auth_routes, dashboard_routes

app = FastAPI(title="StudyBot Pro Dashboard", docs_url=None, redoc_url=None)

BASE_DIR = Path(__file__).parent

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

app.include_router(auth_routes.router)
app.include_router(dashboard_routes.router)