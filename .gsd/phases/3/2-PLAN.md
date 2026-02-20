---
phase: 3
plan: 2
wave: 1
gap_closure: false
---

# Plan 3.2: Job Router & FastAPI App Factory

## Objective

Wire up the FastAPI application with three endpoints (`/availability`, `/input_schema`, `/start_job`) and the `create_app()` factory function. The repo is attached to `app.state` and injected into routes via `Depends(get_repo)`.

## Context

Load these files for context:
- `.gsd/CONTEXT.md` → Sections: "Endpoints Contract", "Error Handling"
- `.gsd/PHASE_3.md` → `app/routers/jobs.py`, `app/main.py`
- `app/utils/hashing.py` (Plan 3.1)
- `app/schemas/requests.py` (Plan 3.1)
- `app/services/job_service.py` (Phase 2)
- `app/repository/job_repo.py` (Phase 2)

## Tasks

<task type="auto">
  <name>Create app/routers/__init__.py and app/routers/jobs.py</name>
  <files>app/routers/__init__.py, app/routers/jobs.py</files>
  <action>
    1. Create `app/routers/__init__.py` as a completely empty file.

    2. Create `app/routers/jobs.py` with exactly this implementation:

    ```python
    from fastapi import APIRouter, Depends, Request
    from fastapi.responses import JSONResponse

    from app.domain.models import Job
    from app.repository.job_repo import InMemoryJobRepository
    from app.schemas.requests import StartJobRequest
    from app.services import job_service
    from app.utils.hashing import hash_inputs

    router = APIRouter()


    def get_repo(request: Request) -> InMemoryJobRepository:
        return request.app.state.repo


    @router.get("/availability")
    def availability(repo: InMemoryJobRepository = Depends(get_repo)):
        return {"available": True, "queue_depth": repo.count()}


    @router.get("/input_schema")
    def input_schema():
        return StartJobRequest.model_json_schema()


    @router.post("/start_job", status_code=201)
    def start_job(
        body: StartJobRequest,
        repo: InMemoryJobRepository = Depends(get_repo),
    ) -> Job:
        input_hash = hash_inputs(body.inputs)
        job = job_service.create_job(repo, input_hash)
        return job
    ```

    AVOID:
    - Do NOT instantiate `InMemoryJobRepository()` inside any route handler — always get it from `app.state` via `get_repo`.
    - Do NOT use `async def` for route handlers — keep them synchronous (no `await` needed, repo is thread-safe already).
    - Do NOT hardcode the schema dict — use `StartJobRequest.model_json_schema()` directly.
    - Do NOT return `job.model_dump()` — return the `Job` object directly; FastAPI will serialize it.
    - The `/start_job` endpoint MUST return HTTP 201, not 200.
  </action>
  <verify>python -c "from app.routers.jobs import router; print('router OK', [r.path for r in router.routes])"</verify>
  <done>
    - `app/routers/__init__.py` exists and is empty.
    - `app/routers/jobs.py` imports cleanly.
    - `router.routes` contains exactly 3 routes: `/availability`, `/input_schema`, `/start_job`.
    - `get_repo` reads from `request.app.state.repo`, never instantiates a new repo.
  </done>
</task>

<task type="auto">
  <name>Create app/main.py</name>
  <files>app/main.py</files>
  <action>
    Create `app/main.py` with exactly this implementation:

    ```python
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
    ```

    AVOID:
    - Do NOT put `app.state.repo = repo` AFTER `app.include_router(jobs.router)` in test isolation — order shown above is correct: state is set before router is included.
    - Do NOT add any middleware, CORS, or lifespan handlers in this phase — keep it minimal.
    - Do NOT import `InMemoryJobRepository` inside `create_app` lazily — import at module top.
    - `app = create_app()` at module level is REQUIRED — uvicorn needs this for production: `uvicorn app.main:app`.
    - The factory function MUST be named `create_app` exactly — tests call `create_app()` directly to get fresh instances.
  </action>
  <verify>python -c "from app.main import create_app; app=create_app(); print('app OK, routes:', [r.path for r in app.routes])"</verify>
  <done>
    - `app/main.py` imports cleanly.
    - `create_app()` returns a `FastAPI` instance with 3 routes: `/availability`, `/input_schema`, `/start_job`.
    - `create_app().state.repo` is an `InMemoryJobRepository` instance.
    - Each call to `create_app()` returns a FRESH app with an empty repo — required for test isolation.
  </done>
</task>

## Must-Haves

- [ ] `app/routers/__init__.py` exists (empty)
- [ ] `app/routers/jobs.py` — 3 endpoints, `get_repo` dependency, no repo instantiation in handlers
- [ ] `app/main.py` — `create_app()` factory, `app.state.repo` attached, module-level `app` instance
- [ ] `/start_job` returns HTTP 201
- [ ] Repo never instantiated inside a route handler

## Success Criteria

- [ ] `python -c "from app.main import create_app; app=create_app()"` exits 0
- [ ] `create_app().state.repo` is `InMemoryJobRepository`
- [ ] Routes: `/availability` (GET), `/input_schema` (GET), `/start_job` (POST 201)
- [ ] All tasks verified passing
