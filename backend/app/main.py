from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.applications import router as applications_router
from app.api.career import router as career_router
from app.api.demo import router as demo_router
from app.api.facts import router as facts_router
from app.api.jobs import router as jobs_router
from app.api.proposals import router as proposals_router
from app.api.requirements import router as requirements_router
from app.core.config import get_settings

app = FastAPI(title="CareerPR", version="0.0.1")

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(facts_router)
app.include_router(jobs_router)
app.include_router(requirements_router)
app.include_router(proposals_router)
app.include_router(applications_router)
app.include_router(career_router)
app.include_router(demo_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


_FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
if _FRONTEND.is_dir():
    app.mount("/ui", StaticFiles(directory=_FRONTEND, html=True), name="ui")


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse("/ui/demo.html")
