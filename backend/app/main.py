from fastapi import FastAPI

from app.api.facts import router as facts_router

app = FastAPI(title="CareerPR", version="0.0.1")
app.include_router(facts_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
