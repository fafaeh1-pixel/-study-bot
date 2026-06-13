from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pathlib import Path

from dashboard.routes.dashboard_routes import router as dashboard_router
from dashboard.routes.students_routes import router as students_router

app = FastAPI(title="StudyBot Pro Dashboard", version="0.1.0")

app.mount(
    "/static",
    StaticFiles(directory=str(Path(__file__).parent / "dashboard" / "static")),
    name="static",
)

app.include_router(dashboard_router)
app.include_router(students_router)