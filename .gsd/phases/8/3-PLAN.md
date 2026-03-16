---
phase: 8
plan: 3
wave: 2
gap_closure: false
---

# Plan 8.3: Refactoring the Router & Wiring Middleware

## Objective

1. Inject `BackgroundTasks` into `/start_job` and `/provide_input` so both endpoints
   return immediately and enqueue `execute_agent_task` to run after the response is sent.
2. Wire `SlowAPIMiddleware` into `create_app()` and decorate `/start_job` with
   `@limiter.limit("5/minute")`.

## Context

### Current state — `app/routers/jobs.py` (58 lines)

```python
@router.post("/start_job", status_code=201, response_model=Job, response_model_by_alias=True)
async def start_job(body: StartJobRequest, repo=Depends(get_repo)) -> Job:
    job = await job_service.create_job(repo, hash_inputs(body.inputs))
    return job                          # job is AWAITING_PAYMENT — never moves further

@router.post("/provide_input", response_model=Job, response_model_by_alias=True)
def provide_input(body: ProvideInputRequest, repo=Depends(get_repo)) -> Job:
    ...
    job_service.advance_job_state(repo, body.job_id, JobStatus.RUNNING)
    updated = job_service.advance_job_state(repo, body.job_id, JobStatus.COMPLETED, ...)
    return updated                      # completes synchronously — blocks the worker
```

### Target state

- `/start_job` — still creates the job (AWAITING_PAYMENT), now also enqueues
  `execute_agent_task` so that the mock simulation runs in the background.
  *Note: in real flow the agent would only start after `/provide_input`; this is
  the agreed simplified behaviour for Phase 8.*
- `/provide_input` — transitions AWAITING_PAYMENT → RUNNING synchronously, then
  enqueues `execute_agent_task`; returns the job in state **RUNNING** (not COMPLETED).
  The background task will eventually move it to COMPLETED.
- Rate limit: `/start_job` allows **5 requests per minute** per IP.

## Tasks

<task type="auto">
  <name>Refactor app/routers/jobs.py</name>
  <files>app/routers/jobs.py</files>
  <action>
    Replace the entire file with:

    ```python
    from fastapi import APIRouter, BackgroundTasks, Depends, Request
    from fastapi.responses import JSONResponse

    from app.core.config import limiter
    from app.domain.models import Job, JobStatus
    from app.repository.job_repo import InMemoryJobRepository
    from app.schemas.requests import StartJobRequest, ProvideInputRequest
    from app.services import job_service
    from app.services.agent_runner import execute_agent_task
    from app.utils.hashing import hash_inputs
    from app.utils.signatures import verify_signature

    router = APIRouter()


    def get_repo(request: Request) -> InMemoryJobRepository:
        return request.app.state.repo


    @router.get("/availability")
    def availability():
        return {"status": "available", "service_type": "masumi-agent"}


    @router.get("/input_schema")
    def input_schema():
        return StartJobRequest.model_json_schema()


    @router.post("/start_job", status_code=201, response_model=Job, response_model_by_alias=True)
    @limiter.limit("5/minute")
    async def start_job(
        request: Request,
        body: StartJobRequest,
        background_tasks: BackgroundTasks,
        repo: InMemoryJobRepository = Depends(get_repo),
    ) -> Job:
        input_hash = hash_inputs(body.inputs)
        job = await job_service.create_job(repo, input_hash)
        background_tasks.add_task(execute_agent_task, job.job_id, repo)
        return job


    @router.get("/status/{job_id}", response_model=Job, response_model_by_alias=True)
    def get_status(
        job_id: str,
        repo: InMemoryJobRepository = Depends(get_repo),
    ) -> Job:
        return repo.get(job_id)


    @router.post("/provide_input", response_model=Job, response_model_by_alias=True)
    async def provide_input(
        body: ProvideInputRequest,
        background_tasks: BackgroundTasks,
        repo: InMemoryJobRepository = Depends(get_repo),
    ) -> Job:
        repo.get(body.job_id)  # raises JobNotFoundError if missing
        verify_signature(body.job_id, body.signature)  # raises InvalidSignatureError if invalid
        updated = job_service.advance_job_state(repo, body.job_id, JobStatus.RUNNING)
        background_tasks.add_task(execute_agent_task, body.job_id, repo)
        return updated
    ```

    KEY POINTS:
    - `@limiter.limit("5/minute")` must be placed **below** `@router.post(...)` and
      `request: Request` must be an explicit parameter — both are slowapi requirements.
    - `/provide_input` now returns the job in **RUNNING** state; `execute_agent_task`
      moves it to COMPLETED asynchronously.
    - The synchronous double-advance in the old `provide_input` is removed.
  </action>
  <verify>python -c "from app.routers.jobs import router; print('router OK')"</verify>
</task>

<task type="auto">
  <name>Wire SlowAPIMiddleware into app/main.py</name>
  <files>app/main.py</files>
  <action>
    Add two new imports at the top (after existing FastAPI imports):

    ```python
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware

    from app.core.config import limiter
    ```

    Inside `create_app()`, **before** `app.include_router(jobs.router)`, add:

    ```python
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    ```

    KEY POINTS:
    - `app.state.limiter = limiter` is required by slowapi to locate the limiter
      instance at request time.
    - `add_middleware` must come before `include_router` to ensure the middleware
      wraps all routes.
    - The existing 6 exception handlers (`RequestValidationError`, `JobNotFoundError`,
      `InvalidStateTransitionError`, `InvalidSignatureError`, `ResponseHandlingException`,
      `UnexpectedResponse`) are unchanged.
  </action>
  <verify>python -c "from app.main import create_app; app = create_app(); print('create_app OK')"</verify>
</task>

## Must-Haves

- [ ] `start_job` injects `BackgroundTasks` and calls `background_tasks.add_task(execute_agent_task, ...)`
- [ ] `provide_input` injects `BackgroundTasks` and enqueues `execute_agent_task` after advancing to RUNNING
- [ ] `provide_input` returns job in **RUNNING** state (not COMPLETED)
- [ ] `start_job` decorated with `@limiter.limit("5/minute")`
- [ ] `SlowAPIMiddleware` wired in `create_app()` before `include_router`
- [ ] `RateLimitExceeded` handler registered (returns 429)
- [ ] `python -c "from app.main import create_app; app = create_app(); print('create_app OK')"` → OK

## Success Criteria

- `curl -X POST /start_job` 6× in quick succession → 6th call returns HTTP 429
- `POST /provide_input` → response body has `"status": "running"` (not `"completed"`)
