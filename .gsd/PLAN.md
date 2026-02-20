---
phase: 4
plan: 1
wave: 1
gap_closure: false
---

# Plan 4.1: ProvideInputRequest Schema & Signature Verifier

## Objective

Extend the request schemas with `ProvideInputRequest` and create the mock Ed25519 signature verifier. Pure Python — no HTTP, no FastAPI.

## Context

- `app/schemas/requests.py` (Phase 3 — contains `StartJobRequest`)
- `app/domain/exceptions.py` (Phase 1 — contains `InvalidSignatureError`)

## Tasks

<task type="auto">
  <name>Add ProvideInputRequest to app/schemas/requests.py</name>
  <files>app/schemas/requests.py</files>
  <action>
    Extend `app/schemas/requests.py` by ADDING `ProvideInputRequest` after the existing `StartJobRequest`. Final file:

    ```python
    from typing import Any

    from pydantic import BaseModel, ConfigDict


    class StartJobRequest(BaseModel):
        model_config = ConfigDict(extra='forbid')

        inputs: dict[str, Any]


    class ProvideInputRequest(BaseModel):
        model_config = ConfigDict(extra='forbid')

        job_id: str
        signature: str
        data: dict[str, Any]
    ```

    AVOID:
    - Do NOT remove or modify `StartJobRequest` — Phase 3 tests depend on it.
    - `extra='forbid'` — extra fields must cause 422.
    - All 3 fields required — no Optional, no defaults.
    - No fastapi imports — pure Pydantic only.
  </action>
  <verify>python -c "from app.schemas.requests import StartJobRequest, ProvideInputRequest; r=ProvideInputRequest(job_id='j1', signature='s1', data={}); print('schema OK', r.job_id)"</verify>
  <done>
    - Both classes importable.
    - `ProvideInputRequest(job_id='j1', signature='s1', data={})` succeeds.
    - Extra field raises `ValidationError`.
    - `StartJobRequest` still works.
  </done>
</task>

<task type="auto">
  <name>Create app/utils/signatures.py</name>
  <files>app/utils/signatures.py</files>
  <action>
    Create `app/utils/signatures.py` with exactly this:

    ```python
    from app.domain.exceptions import InvalidSignatureError


    def verify_signature(job_id: str, signature: str) -> None:
        """
        Mock Ed25519 verification.
        Contract: signature MUST equal "valid_sig_" + job_id
        Raises InvalidSignatureError on mismatch.
        """
        expected = f"valid_sig_{job_id}"
        if signature != expected:
            raise InvalidSignatureError(f"Signature mismatch for job {job_id!r}")
    ```

    AVOID:
    - No external crypto library — mock only.
    - Return type MUST be `None`.
    - Raise `InvalidSignatureError` — NOT `HTTPException`.
    - Pure function, no side effects.
  </action>
  <verify>python -c "from app.utils.signatures import verify_signature; verify_signature('j1', 'valid_sig_j1'); print('sig OK')"</verify>
  <done>
    - `verify_signature('j1', 'valid_sig_j1')` → None (no exception).
    - `verify_signature('j1', 'wrong')` → raises `InvalidSignatureError`.
  </done>
</task>

## Must-Haves

- [ ] Both `StartJobRequest` AND `ProvideInputRequest` in `requests.py`
- [ ] `ProvideInputRequest`: `extra='forbid'`, fields: `job_id: str`, `signature: str`, `data: dict[str, Any]`
- [ ] `verify_signature()` raises `InvalidSignatureError` on mismatch, no external crypto

## Success Criteria

- [ ] `from app.schemas.requests import StartJobRequest, ProvideInputRequest` exits 0
- [ ] `verify_signature('j', 'valid_sig_j')` passes silently
- [ ] `verify_signature('j', 'bad')` raises `InvalidSignatureError`

---
---
phase: 4
plan: 2
wave: 1
gap_closure: false
---

# Plan 4.2: Final Endpoints & Global Exception Handlers

## Objective

Add `GET /status/{job_id}` and `POST /provide_input` to the router, and wire four global exception handlers into `create_app()`.

## Context

- `app/routers/jobs.py` (Phase 3 — 3 existing routes)
- `app/main.py` (Phase 3 — `create_app()`)
- `app/utils/signatures.py` (Plan 4.1)
- `app/schemas/requests.py` (Plan 4.1 — `ProvideInputRequest`)

## Tasks

<task type="auto">
  <name>Extend app/routers/jobs.py with /status and /provide_input</name>
  <files>app/routers/jobs.py</files>
  <action>
    EXTEND `app/routers/jobs.py`. Do NOT modify existing routes. The final file:

    ```python
    from fastapi import APIRouter, Depends, Request

    from app.domain.models import Job, JobStatus
    from app.repository.job_repo import InMemoryJobRepository
    from app.schemas.requests import StartJobRequest, ProvideInputRequest
    from app.services import job_service
    from app.utils.hashing import hash_inputs
    from app.utils.signatures import verify_signature

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

    AVOID:
    - Do NOT remove or modify existing routes — Phase 3 tests depend on them.
    - Do NOT catch domain errors inline — let them bubble to global handlers.
    - `/provide_input`: `repo.get()` BEFORE `verify_signature()` — 404 takes priority over 403.
    - `result="Task executed successfully"` — exact string.
  </action>
  <verify>python -c "from app.routers.jobs import router; paths=[r.path for r in router.routes]; assert '/status/{job_id}' in paths and '/provide_input' in paths; print('routes OK', paths)"</verify>
  <done>
    - 5 routes: `/availability`, `/input_schema`, `/start_job`, `/status/{job_id}`, `/provide_input`.
    - `JobStatus` imported.
    - Phase 3 routes untouched.
  </done>
</task>

<task type="auto">
  <name>Add global exception handlers to app/main.py</name>
  <files>app/main.py</files>
  <action>
    Replace `app/main.py` with this complete implementation:

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
    - Handlers MUST be `async def` — required by FastAPI.
    - Handlers defined INSIDE `create_app()` using `@app.exception_handler(...)`.
    - `RequestValidationError` handler MUST include `"body": exc.body`.
    - `app = create_app()` at module level MUST remain.
    - No inline `HTTPException` for domain errors.
  </action>
  <verify>python -c "from app.main import create_app; app=create_app(); print('handlers OK:', len(app.exception_handlers), 'registered')"</verify>
  <done>
    - `create_app()` exits 0.
    - All Phase 3 behaviour preserved.
    - 4 custom exception handlers registered.
  </done>
</task>

## Must-Haves

- [ ] 5 routes: Phase 3 routes + `/status/{job_id}` + `/provide_input`
- [ ] `/provide_input`: `repo.get()` BEFORE `verify_signature()`
- [ ] Both state advances: AWAITING_PAYMENT→RUNNING, then RUNNING→COMPLETED
- [ ] 4 global handlers: 422 / 404 / 409 / 403

## Success Criteria

- [ ] `router.routes` has 5 entries
- [ ] All Phase 3 routes still pass
- [ ] `create_app()` has 4 custom exception handlers

---
---
phase: 4
plan: 3
wave: 2
gap_closure: false
---

# Plan 4.3: Phase 4 Test Suite

## Objective

Write and pass the complete Pytest verification suite for Phase 4. All 8 test cases must pass. Runs AFTER Plans 4.1 and 4.2 complete.

## Context

- `.gsd/PHASE_4.md` → "Verification Criteria" section
- `app/main.py`, `app/routers/jobs.py`, `app/utils/signatures.py`

## Tasks

<task type="auto">
  <name>Create tests/test_phase4_full_flow.py</name>
  <files>tests/test_phase4_full_flow.py</files>
  <action>
    Create `tests/test_phase4_full_flow.py` with ALL 8 test cases:

    ```python
    import pytest
    import httpx

    from app.main import create_app


    @pytest.fixture
    def client():
        app = create_app()
        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        )


    async def _create_job(c: httpx.AsyncClient) -> dict:
        r = await c.post("/start_job", json={"inputs": {"task": "test_task"}})
        assert r.status_code == 201
        return r.json()


    # TC-4.1: GET /status/{job_id} returns the correct job
    @pytest.mark.asyncio
    async def test_get_status_returns_job(client):
        async with client as c:
            job = await _create_job(c)
            r = await c.get(f"/status/{job['job_id']}")
        assert r.status_code == 200
        assert r.json()["job_id"] == job["job_id"]


    # TC-4.2: GET /status with unknown ID returns 404
    @pytest.mark.asyncio
    async def test_get_status_unknown_job(client):
        async with client as c:
            r = await c.get("/status/nonexistent-000")
        assert r.status_code == 404
        assert "not found" in r.json()["detail"].lower()


    # TC-4.3: POST /provide_input with valid signature completes the job
    @pytest.mark.asyncio
    async def test_provide_input_valid_signature(client):
        async with client as c:
            job = await _create_job(c)
            job_id = job["job_id"]
            r = await c.post("/provide_input", json={
                "job_id": job_id,
                "signature": f"valid_sig_{job_id}",
                "data": {"confirmation": "payment_received"},
            })
        assert r.status_code == 200
        assert r.json()["status"] == "completed"
        assert r.json()["result"] is not None


    # TC-4.4: POST /provide_input with invalid signature returns 403
    @pytest.mark.asyncio
    async def test_provide_input_invalid_signature(client):
        async with client as c:
            job = await _create_job(c)
            r = await c.post("/provide_input", json={
                "job_id": job["job_id"],
                "signature": "wrong_signature",
                "data": {},
            })
        assert r.status_code == 403


    # TC-4.5: POST /provide_input for unknown job returns 404
    @pytest.mark.asyncio
    async def test_provide_input_unknown_job(client):
        async with client as c:
            r = await c.post("/provide_input", json={
                "job_id": "ghost-job-id",
                "signature": "valid_sig_ghost-job-id",
                "data": {},
            })
        assert r.status_code == 404


    # TC-4.6: POST /provide_input with extra fields returns 422
    @pytest.mark.asyncio
    async def test_provide_input_rejects_extra_fields(client):
        async with client as c:
            job = await _create_job(c)
            r = await c.post("/provide_input", json={
                "job_id": job["job_id"],
                "signature": f"valid_sig_{job['job_id']}",
                "data": {},
                "evil_extra": "hacked",
            })
        assert r.status_code == 422


    # TC-4.7: 422 response body is JSON with "detail" key
    @pytest.mark.asyncio
    async def test_422_response_shape(client):
        async with client as c:
            r = await c.post("/start_job", json={"bad_field": "no_inputs"})
        assert r.status_code == 422
        body = r.json()
        assert "detail" in body


    # TC-4.8: Full lifecycle — awaiting_payment -> running -> completed
    @pytest.mark.asyncio
    async def test_full_job_lifecycle(client):
        async with client as c:
            job = await _create_job(c)
            assert job["status"] == "awaiting_payment"
            job_id = job["job_id"]

            r = await c.post("/provide_input", json={
                "job_id": job_id,
                "signature": f"valid_sig_{job_id}",
                "data": {"confirm": True},
            })
            final = r.json()
            assert final["status"] == "completed"

            status_r = await c.get(f"/status/{job_id}")
            assert status_r.json()["status"] == "completed"
    ```

    KEY: `_create_job(c)` takes an already-opened client `c`. Call it inside `async with client as c:`.

    AVOID:
    - Do NOT use `TestClient`.
    - Each test get its own fresh app via the fixture.
    - TC-4.8 must share state — all 3 requests in ONE `async with client as c:` block.
  </action>
  <verify>pytest tests/test_phase4_full_flow.py -v</verify>
  <done>
    - 8 passed, 0 failed.
    - TC-4.2 has "not found" in detail.
    - TC-4.8 full lifecycle works end-to-end.
  </done>
</task>

<task type="auto">
  <name>Run combined Phase 1+2+3+4 gate check</name>
  <files>(no new files)</files>
  <action>
    Run: `pytest tests/ -v --tb=short`

    Common failures:
    - 500 instead of 404/403 → exception handler not in `create_app()`.
    - TC-4.2 "not found" fails → check `str(JobNotFoundError)` contains "not found".
    - TC-4.6 gets 200 → `ProvideInputRequest` needs `extra='forbid'`.
    - TC-4.3 result is None → check `result="Task executed successfully"` in second `advance_job_state`.
    - Phase 3 breaks → `StartJobRequest` removed from `requests.py` — must have BOTH classes.

    AVOID: Do NOT modify test files.
  </action>
  <verify>pytest tests/ -v --tb=short 2>&1 | tail -5</verify>
  <done>
    - `pytest tests/` → **37 passed, 0 failed** (Phase 1: 13 + Phase 2: 8 + Phase 3: 8 + Phase 4: 8)
    - Exit code: 0
  </done>
</task>

## Must-Haves

- [ ] 8 test functions in `test_phase4_full_flow.py`
- [ ] `_create_job(c)` helper called with open client inside `async with`
- [ ] TC-4.8 all requests in ONE `async with client as c:` block

## Success Criteria

- [ ] `pytest tests/test_phase4_full_flow.py -v` → **8 passed, 0 failed**
- [ ] `pytest tests/` → **37 passed, 0 failed**
- [ ] Exit code: `0`
