from fastapi import FastAPI

from app.repository.job_repo import InMemoryJobRepository
from app.routers import jobs


def create_app() -> FastAPI:
    app = FastAPI(title="Masumi MIP-003 Gateway", version="1.0.0")
    repo = InMemoryJobRepository()
    app.state.repo = repo
    app.include_router(jobs.router)
    return app


app = create_app()
