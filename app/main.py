from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import limiter
from app.domain.exceptions import (
    InvalidSignatureError,
    InvalidStateTransitionError,
    JobNotFoundError,
)
from app.repository.job_repo import InMemoryJobRepository
from app.routers import jobs


def create_app() -> FastAPI:
    app = FastAPI(title="Masumi MIP-003 Gateway", version="1.0.0")

    # --- Rate limiting (no SlowAPIMiddleware — uses decorator-only mode) ---
    # SlowAPIMiddleware uses BaseHTTPMiddleware which conflicts with custom
    # exception handlers that also write responses (known Starlette issue).
    # The @limiter.limit() decorator + this handler is sufficient.
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # --- App state & routes ---
    repo = InMemoryJobRepository()
    app.state.repo = repo
    app.include_router(jobs.router)

    # --- Exception handlers ---
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

    @app.exception_handler(ResponseHandlingException)
    async def qdrant_response_handling_handler(
        request: Request, exc: ResponseHandlingException
    ):
        return JSONResponse(
            status_code=503,
            content={"detail": "Vector database temporarily unavailable. Please try again later."},
        )

    @app.exception_handler(UnexpectedResponse)
    async def qdrant_unexpected_response_handler(
        request: Request, exc: UnexpectedResponse
    ):
        return JSONResponse(
            status_code=503,
            content={"detail": "Vector database temporarily unavailable. Please try again later."},
        )

    return app


app = create_app()
