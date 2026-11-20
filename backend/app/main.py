from fastapi import FastAPI

from app.api.facts import router as facts_router
from app.api.jobs import router as jobs_router

app = FastAPI(title="CareerPR", version="0.0.1")
app.include_router(facts_router)
app.include_router(jobs_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
