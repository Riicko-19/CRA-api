---
phase: 4
plan: 2
wave: 1
gap_closure: false
---

# Plan 4.2: Final Endpoints & Global Exception Handlers

## Objective

Add the final two endpoints (`GET /status/{job_id}`, `POST /provide_input`) to the jobs router, and wire four global exception handlers into the `create_app()` factory. This is the last implementation wave.

## Context

Load these files for context:
- `.gsd/CONTEXT.md` → Sections: "Endpoints Contract", "Error Handling"
- `.gsd/PHASE_4.md` → `app/routers/jobs.py`, `app/main.py`
- `app/routers/jobs.py` (Phase 3 — contains 3 existing routes)
- `app/main.py` (Phase 3 — contains `create_app()`)
- `app/utils/signatures.py` (Plan 4.1)
- `app/schemas/requests.py` (Plan 4.1 — contains `ProvideInputRequest`)
- `app/services/job_service.py` (Phase 2 — `advance_job_state`)

## Tasks

<task type="auto">
  <name>Extend app/routers/jobs.py with /status and /provide_input</name>
  <files>app/routers/jobs.py</files>
  <action>
    Extend `app/routers/jobs.py` by ADDING two new endpoints. Do NOT modify or remove any existing Phase 3 routes.

    Add the following imports at the top (merge with the existing import block):
    ```python
    from app.schemas.requests import StartJobRequest, ProvideInputRequest
    from app.utils.signatures import verify_signature
    ```

    Add the following two routes at the END of the file:

    ```python
    @router.get("/status/{job_id}")
    def get_status(
        job_id: str,
        repo: InMemoryJobRepository = Depends(get_repo),
    ) -> Job:
        return repo.get(job_id)


    @router.post("/provide_input")
    def provide_input(
        body: ProvideInputRequest,
        repo: InMemoryJobRepository = Depends(get_repo),
    ) -> Job:
        repo.get(body.job_id)  # raises JobNotFoundError if missing
        verify_signature(body.job_id, body.signature)  # raises InvalidSignatureError if invalid
        job_service.advance_job_state(repo, body.job_id, JobStatus.RUNNING)
        updated = job_service.advance_job_state(
            repo, body.job_id, JobStatus.COMPLETED, result="Task executed successfully"
        )
        return updated
    ```

    Also add to the imports at the top of the file:
    ```python
    from app.domain.models import Job, JobStatus
    ```
    (Replace the existing `from app.domain.models import Job` line — add `JobStatus` to it)

    AVOID:
    - Do NOT remove or modify `/availability`, `/input_schema`, or `/start_job` — Phase 3 tests depend on them.
    - Do NOT catch `JobNotFoundError` or `InvalidSignatureError` inline — let them bubble up to the global handlers.
    - Do NOT add `status_code` to `/status` or `/provide_input` — both return 200 by default.
    - `/provide_input` MUST call `repo.get(job_id)` BEFORE `verify_signature()` — 404 takes priority over 403.
    - Both state advances MUST be two separate calls: AWAITING_PAYMENT→RUNNING, then RUNNING→COMPLETED.
    - `result="Task executed successfully"` — exact string, no variation.
  </action>
  <verify>python -c "from app.routers.jobs import router; paths=[r.path for r in router.routes]; assert '/status/{job_id}' in paths and '/provide_input' in paths; print('routes OK', paths)"</verify>
  <done>
    - `router.routes` has 5 entries: `/availability`, `/input_schema`, `/start_job`, `/status/{job_id}`, `/provide_input`.
    - Phase 3 routes are untouched.
    - `JobStatus` is imported in the file.
    - `verify_signature` is imported from `app.utils.signatures`.
    - `ProvideInputRequest` is imported from `app.schemas.requests`.
  </done>
</task>

<task type="auto">
  <name>Add global exception handlers to app/main.py</name>
  <files>app/main.py</files>
  <action>
    Extend `app/main.py` by adding four global exception handlers inside `create_app()`. The final file must be exactly:

    ```python
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
    ```

    AVOID:
    - Exception handlers MUST be defined INSIDE `create_app()` using `@app.exception_handler(...)` — NOT `@app.add_exception_handler(...)` at module level.
    - Do NOT use `HTTPException` for domain errors — use only the custom exception handlers.
    - The `RequestValidationError` handler MUST include `"body": exc.body` — required for TC-4.7.
    - Module-level `app = create_app()` MUST remain — uvicorn needs it.
    - Handlers are `async def` — this is required by FastAPI's handler protocol.
    - `create_app()` must still set `app.state.repo` and include the jobs router — do not remove those lines.
  </action>
  <verify>python -c "from app.main import create_app; app=create_app(); handlers=list(app.exception_handlers.keys()); print('handlers OK:', [h.__name__ if hasattr(h,'__name__') else h for h in handlers])"</verify>
  <done>
    - `app.exception_handlers` has 4 custom handlers registered.
    - `from app.main import create_app; create_app()` exits 0.
    - All Phase 3 behaviour preserved — `app.state.repo` set, jobs router included, 5 routes total.
  </done>
</task>

## Must-Haves

- [ ] `app/routers/jobs.py` — 5 routes total: all Phase 3 routes + `/status/{job_id}` (GET) + `/provide_input` (POST)
- [ ] `/provide_input` — `repo.get()` called BEFORE `verify_signature()` (404 priority over 403)
- [ ] Both state advances are separate calls: AWAITING_PAYMENT→RUNNING, RUNNING→COMPLETED
- [ ] `result="Task executed successfully"` — exact string
- [ ] `app/main.py` — 4 global handlers: `RequestValidationError` (422), `JobNotFoundError` (404), `InvalidStateTransitionError` (409), `InvalidSignatureError` (403)
- [ ] No inline `HTTPException` for domain errors — all via global handlers

## Success Criteria

- [ ] `router.routes` has 5 entries including `/status/{job_id}` and `/provide_input`
- [ ] `create_app().exception_handlers` has 4 custom handlers
- [ ] All tasks verified passing
