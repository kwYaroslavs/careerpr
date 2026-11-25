from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.applications import router as applications_router
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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
