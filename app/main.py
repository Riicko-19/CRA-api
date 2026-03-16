import logging
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.adapters.api_key_auth_adapter import ApiKeyAuthAdapter
from app.adapters.llm_normalisation_adapter import LLMNormalisationAdapter
from app.adapters.masumi_payment import MasumiPaymentAdapter
from app.adapters.orchestrator_adapter import OrchestratorAdapter
from app.core.config import limiter, settings
from app.core.logging import configure_logging
from app.domain.exceptions import (
    InvalidSignatureError,
    InvalidStateTransitionError,
    JobNotFoundError,
)
from app.repository.qdrant_job_repo import QdrantJobRepository
from app.routers import jobs


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if hasattr(app.state, "repo") and hasattr(app.state.repo, "recover_stale_running_jobs"):
        recovered = app.state.repo.recover_stale_running_jobs(timeout_minutes=settings.job_timeout_minutes)
        logger.info(
            "Startup recovery complete",
            extra={"job_id": "startup", "from_state": "running", "to_state": f"failed:{recovered}"},
        )
    yield


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="Masumi MIP-003 Gateway", version="1.0.0", lifespan=lifespan)

    # --- Rate limiting ---
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # --- App state & routes ---
    repo = QdrantJobRepository()
    payment = MasumiPaymentAdapter()
    auth = ApiKeyAuthAdapter()
    normaliser = LLMNormalisationAdapter()
    orchestrator = OrchestratorAdapter()
    app.state.repo = repo
    app.state.payment = payment
    app.state.auth = auth
    app.state.normaliser = normaliser
    app.state.orchestrator = orchestrator

    allowed_origins = [origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_middleware(request: Request, call_next):
        request_id = str(uuid4())
        request.state.request_id = request_id

        exempt_paths = {
            "/availability",
            "/input_schema",
            "/v1/availability",
            "/v1/input_schema",
        }
        if request.url.path not in exempt_paths:
            provided = request.headers.get("X-API-Key")
            if not app.state.auth.is_authorized(provided):
                logger.error(
                    "Unauthorized request",
                    extra={
                        "request_id": request_id,
                        "path": request.url.path,
                        "method": request.method,
                        "status_code": 401,
                    },
                )
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid or missing API key.", "request_id": request_id},
                )

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        if request.url.path in {"/availability", "/input_schema", "/start_job", "/provide_input"} or request.url.path.startswith("/status/"):
            response.headers["Warning"] = '299 - "Deprecated route, use /v1 prefixed endpoints"'

        logger.info(
            "Request completed",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "status_code": response.status_code,
            },
        )
        return response

    app.include_router(jobs.router, prefix="/v1")
    app.include_router(jobs.router)

    def _error_content(request: Request, detail, extra: dict | None = None) -> dict:
        request_id = getattr(request.state, "request_id", "unknown")
        payload = {"detail": detail, "request_id": request_id}
        if extra:
            payload.update(extra)
        return payload

    # --- Exception handlers ---
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.error(
            "Validation error",
            extra={"request_id": getattr(request.state, "request_id", "unknown"), "path": request.url.path, "method": request.method, "status_code": 422},
        )
        return JSONResponse(
            status_code=422,
            content=_error_content(request, exc.errors(), extra={"body": exc.body}),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        logger.error(
            "HTTP exception",
            extra={"request_id": getattr(request.state, "request_id", "unknown"), "path": request.url.path, "method": request.method, "status_code": exc.status_code},
        )
        return JSONResponse(status_code=exc.status_code, content=_error_content(request, exc.detail))

    @app.exception_handler(JobNotFoundError)
    async def job_not_found_handler(request: Request, exc: JobNotFoundError):
        logger.error(
            "Job not found",
            extra={"request_id": getattr(request.state, "request_id", "unknown"), "path": request.url.path, "method": request.method, "status_code": 404},
        )
        return JSONResponse(status_code=404, content=_error_content(request, str(exc)))

    @app.exception_handler(InvalidStateTransitionError)
    async def invalid_transition_handler(request: Request, exc: InvalidStateTransitionError):
        logger.error(
            "Invalid transition",
            extra={"request_id": getattr(request.state, "request_id", "unknown"), "path": request.url.path, "method": request.method, "status_code": 409},
        )
        return JSONResponse(status_code=409, content=_error_content(request, str(exc)))

    @app.exception_handler(InvalidSignatureError)
    async def invalid_signature_handler(request: Request, exc: InvalidSignatureError):
        logger.error(
            "Invalid signature",
            extra={"request_id": getattr(request.state, "request_id", "unknown"), "path": request.url.path, "method": request.method, "status_code": 403},
        )
        return JSONResponse(status_code=403, content=_error_content(request, str(exc)))

    @app.exception_handler(ResponseHandlingException)
    async def qdrant_response_handling_handler(
        request: Request, exc: ResponseHandlingException
    ):
        logger.error(
            "Qdrant response handling error",
            extra={"request_id": getattr(request.state, "request_id", "unknown"), "path": request.url.path, "method": request.method, "status_code": 503},
        )
        return JSONResponse(
            status_code=503,
            content=_error_content(request, "Vector database temporarily unavailable. Please try again later."),
        )

    @app.exception_handler(UnexpectedResponse)
    async def qdrant_unexpected_response_handler(
        request: Request, exc: UnexpectedResponse
    ):
        logger.error(
            "Qdrant unexpected response error",
            extra={"request_id": getattr(request.state, "request_id", "unknown"), "path": request.url.path, "method": request.method, "status_code": 503},
        )
        return JSONResponse(
            status_code=503,
            content=_error_content(request, "Vector database temporarily unavailable. Please try again later."),
        )

    @app.exception_handler(Exception)
    async def unexpected_exception_handler(request: Request, exc: Exception):
        logger.exception(
            "Unhandled exception",
            extra={"request_id": getattr(request.state, "request_id", "unknown"), "path": request.url.path, "method": request.method, "status_code": 500},
        )
        return JSONResponse(status_code=500, content=_error_content(request, "Internal server error."))

    return app


app = create_app()