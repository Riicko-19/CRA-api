from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.domain.exceptions import (
    InvalidSignatureError,
    InvalidStateTransitionError,
    JobNotFoundError,
)
from app.repository.job_repo import InMemoryJobRepository
from app.routers import jobs


def create_app() -> FastAPI:
    app = FastAPI(title="Masumi MIP-003 Gateway", version="1.0.0")
    repo = InMemoryJobRepository()
    app.state.repo = repo
    app.include_router(jobs.router)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors(), "body": exc.body},
        )

    @app.exception_handler(JobNotFoundError)
    async def job_not_found_handler(request: Request, exc: JobNotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(InvalidStateTransitionError)
    async def invalid_transition_handler(request: Request, exc: InvalidStateTransitionError):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(InvalidSignatureError)
    async def invalid_signature_handler(request: Request, exc: InvalidSignatureError):
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    return app


app = create_app()
