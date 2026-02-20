---
phase: 3
plan: 1
wave: 1
gap_closure: false
---

# Plan 3.1: Hashing Utility & Request Schemas

## Objective

Implement the deterministic SHA-256 hashing utility and the `StartJobRequest` Pydantic schema. Pure Python — no FastAPI, no I/O. These are the building blocks for the router in Plan 3.2.

## Context

Load these files for context:
- `.gsd/CONTEXT.md` → Sections: "Hashing Contract"
- `.gsd/PHASE_3.md` → `app/utils/hashing.py`, `app/schemas/requests.py`

## Tasks

<task type="auto">
  <name>Create app/utils/__init__.py and app/utils/hashing.py</name>
  <files>app/utils/__init__.py, app/utils/hashing.py</files>
  <action>
    1. Create `app/utils/__init__.py` as a completely empty file.

    2. Create `app/utils/hashing.py` with exactly this:

    ```python
    import hashlib
    import json


    def hash_inputs(payload: dict) -> str:
        """
        Deterministic SHA-256 of a dict.
        sort_keys=True ensures field order independence.
        separators=(',', ':') eliminates whitespace variation.
        """
        canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    ```

    AVOID:
    - Only `hashlib` and `json` — both are stdlib. Zero external deps.
    - Must be `sha256` — not md5, sha1, or any other algorithm.
    - Must use `sort_keys=True` AND `separators=(',', ':')` — both required for determinism.
    - Encoding MUST be `'utf-8'`.
    - No caching, memoization, or side effects.
  </action>
  <verify>python -c "from app.utils.hashing import hash_inputs; h=hash_inputs({'b':2,'a':1}); assert h==hash_inputs({'a':1,'b':2}); assert len(h)==64; print('hashing OK', h[:16])"</verify>
  <done>
    - `app/utils/__init__.py` exists (empty).
    - `hash_inputs({'b':2,'a':1}) == hash_inputs({'a':1,'b':2})` — order independent.
    - `len(hash_inputs({})) == 64`.
  </done>
</task>

<task type="auto">
  <name>Create app/schemas/__init__.py and app/schemas/requests.py</name>
  <files>app/schemas/__init__.py, app/schemas/requests.py</files>
  <action>
    1. Create `app/schemas/__init__.py` as a completely empty file.

    2. Create `app/schemas/requests.py` with exactly this:

    ```python
    from typing import Any

    from pydantic import BaseModel, ConfigDict


    class StartJobRequest(BaseModel):
        model_config = ConfigDict(extra='forbid')

        inputs: dict[str, Any]
    ```

    AVOID:
    - `extra='forbid'` — never 'allow' or 'ignore'. Extra fields must cause 422.
    - No other fields, validators, or methods.
    - No `fastapi` imports here — pure Pydantic only.
  </action>
  <verify>python -c "from app.schemas.requests import StartJobRequest; r=StartJobRequest(inputs={'task':'x'}); print('schema OK', r.inputs)"</verify>
  <done>
    - `StartJobRequest(inputs={'task':'x'})` succeeds.
    - `StartJobRequest(inputs={}, EXTRA='bad')` raises `ValidationError`.
    - `StartJobRequest.model_json_schema()` has `"type": "object"` and `"properties"`.
  </done>
</task>

## Must-Haves

- [ ] `app/utils/hashing.py` — stdlib only, `sort_keys=True`, `separators=(',',':')`
- [ ] `app/schemas/requests.py` — `extra='forbid'`, single `inputs: dict[str, Any]` field

## Success Criteria

- [ ] `hash_inputs({'b':2,'a':1}) == hash_inputs({'a':1,'b':2})` ✓
- [ ] `len(hash_inputs({})) == 64` ✓
- [ ] `StartJobRequest(inputs={}, EXTRA='x')` raises `ValidationError` ✓

---
---
phase: 3
plan: 2
wave: 1
gap_closure: false
---

# Plan 3.2: Job Router & FastAPI App Factory

## Objective

Wire up the FastAPI application with three endpoints (`/availability`, `/input_schema`, `/start_job`) and the `create_app()` factory. Repo is attached to `app.state` and injected via `Depends(get_repo)`.

## Context

Load these files for context:
- `.gsd/CONTEXT.md` → Sections: "Endpoints Contract"
- `.gsd/PHASE_3.md` → `app/routers/jobs.py`, `app/main.py`
- `app/utils/hashing.py`, `app/schemas/requests.py` (Plan 3.1)
- `app/services/job_service.py`, `app/repository/job_repo.py` (Phase 2)

## Tasks

<task type="auto">
  <name>Create app/routers/__init__.py and app/routers/jobs.py</name>
  <files>app/routers/__init__.py, app/routers/jobs.py</files>
  <action>
    1. Create `app/routers/__init__.py` as a completely empty file.

    2. Create `app/routers/jobs.py` with exactly this:

    ```python
    from fastapi import APIRouter, Depends, Request

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
    - Do NOT instantiate `InMemoryJobRepository()` inside any route handler.
    - Do NOT use `async def` for handlers — keep sync.
    - `/start_job` MUST have `status_code=201`.
    - Return `Job` object directly — FastAPI serializes it. Do NOT call `.model_dump()`.
  </action>
  <verify>python -c "from app.routers.jobs import router; print('router OK', [r.path for r in router.routes])"</verify>
  <done>
    - `router.routes` has 3 entries: `/availability`, `/input_schema`, `/start_job`.
    - `get_repo` reads from `request.app.state.repo`.
  </done>
</task>

<task type="auto">
  <name>Create app/main.py</name>
  <files>app/main.py</files>
  <action>
    Create `app/main.py` with exactly this:

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
    - `create_app()` must be the exact function name — tests call it directly.
    - Module-level `app = create_app()` is REQUIRED for uvicorn.
    - No middleware, CORS, or lifespan handlers in this phase.
    - Each `create_app()` call MUST return a fresh app with a fresh repo — test isolation depends on this.
  </action>
  <verify>python -c "from app.main import create_app; app=create_app(); print('app OK, routes:', [r.path for r in app.routes])"</verify>
  <done>
    - `create_app()` returns FastAPI with 3 routes.
    - `create_app().state.repo` is `InMemoryJobRepository`.
    - Module-level `app` exists and is importable.
  </done>
</task>

## Must-Haves

- [ ] `app/routers/jobs.py` — 3 endpoints, `get_repo` dependency, no repo in handlers
- [ ] `app/main.py` — `create_app()` factory, `app.state.repo` set, module-level `app`
- [ ] `/start_job` returns HTTP 201

## Success Criteria

- [ ] `from app.main import create_app; create_app()` exits 0
- [ ] Routes: `/availability` (GET), `/input_schema` (GET), `/start_job` (POST 201)

---
---
phase: 3
plan: 3
wave: 2
gap_closure: false
---

# Plan 3.3: Phase 3 Test Suite

## Objective

Write and pass the complete Pytest verification suite for Phase 3. All 8 test cases must pass using `httpx.AsyncClient` with `ASGITransport`. Runs AFTER Plans 3.1 and 3.2 complete.

## Context

Load these files for context:
- `.gsd/PHASE_3.md` → "Verification Criteria" section
- `app/main.py`, `app/utils/hashing.py`

## Tasks

<task type="auto">
  <name>Create tests/test_phase3_endpoints.py</name>
  <files>tests/test_phase3_endpoints.py</files>
  <action>
    Create `tests/test_phase3_endpoints.py` with ALL 8 test cases exactly as specified:

    ```python
    import hashlib
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


    # TC-3.1: hash_inputs is deterministic (field-order independent)
    def test_hash_inputs_deterministic():
        from app.utils.hashing import hash_inputs
        h1 = hash_inputs({"b": 2, "a": 1})
        h2 = hash_inputs({"a": 1, "b": 2})
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex = 64 chars


    # TC-3.2: hash_inputs produces correct SHA-256
    def test_hash_inputs_correctness():
        from app.utils.hashing import hash_inputs
        payload = {"task": "hello"}
        expected_canonical = '{"task":"hello"}'
        expected_hash = hashlib.sha256(expected_canonical.encode()).hexdigest()
        assert hash_inputs(payload) == expected_hash


    # TC-3.3: GET /availability returns 200 with correct shape
    @pytest.mark.asyncio
    async def test_availability(client):
        async with client as c:
            r = await c.get("/availability")
        assert r.status_code == 200
        data = r.json()
        assert data["available"] is True
        assert isinstance(data["queue_depth"], int)


    # TC-3.4: GET /input_schema returns 200 with a JSON Schema object
    @pytest.mark.asyncio
    async def test_input_schema(client):
        async with client as c:
            r = await c.get("/input_schema")
        assert r.status_code == 200
        schema = r.json()
        assert schema["type"] == "object"
        assert "properties" in schema


    # TC-3.5: POST /start_job creates a job and returns 201
    @pytest.mark.asyncio
    async def test_start_job_creates_job(client):
        async with client as c:
            r = await c.post("/start_job", json={"inputs": {"task": "do_work"}})
        assert r.status_code == 201
        job = r.json()
        assert job["status"] == "awaiting_payment"
        assert len(job["input_hash"]) == 64
        assert job["blockchain_identifier"].startswith("mock_bc_")


    # TC-3.6: POST /start_job with extra top-level fields returns 422
    @pytest.mark.asyncio
    async def test_start_job_rejects_extra_fields(client):
        async with client as c:
            r = await c.post(
                "/start_job",
                json={"inputs": {"task": "x"}, "hacker_field": "evil"},
            )
        assert r.status_code == 422


    # TC-3.7: POST /start_job is deterministic — same inputs produce same hash
    @pytest.mark.asyncio
    async def test_start_job_hash_determinism(client):
        payload = {"inputs": {"b": 2, "a": 1}}
        async with client as c:
            r1 = await c.post("/start_job", json=payload)
            r2 = await c.post("/start_job", json=payload)
        assert r1.json()["input_hash"] == r2.json()["input_hash"]


    # TC-3.8: queue_depth increases after job creation
    @pytest.mark.asyncio
    async def test_queue_depth_increases(client):
        async with client as c:
            before = (await c.get("/availability")).json()["queue_depth"]
            await c.post("/start_job", json={"inputs": {"task": "x"}})
            after = (await c.get("/availability")).json()["queue_depth"]
        assert after == before + 1
    ```

    KEY: TC-3.7 and TC-3.8 share state across requests — they go inside ONE `async with client as c:` block.

    AVOID:
    - Do NOT use `TestClient` — must be `httpx.AsyncClient`.
    - Do NOT add `event_loop` fixtures.
    - Do NOT share `client` across tests — each test uses its own fresh `create_app()`.
  </action>
  <verify>pytest tests/test_phase3_endpoints.py -v</verify>
  <done>
    - `pytest tests/test_phase3_endpoints.py -v` → 8 passed, 0 failed, exit code 0.
    - All `@pytest.mark.asyncio` tests run without event loop errors.
  </done>
</task>

<task type="auto">
  <name>Run combined Phase 1 + 2 + 3 gate check</name>
  <files>(no new files)</files>
  <action>
    Run: `pytest tests/ -v --tb=short`

    Common Phase 3 failure guides:
    - 404 on any endpoint → `app.include_router(jobs.router)` missing in `create_app()`.
    - TC-3.5 returns 200 not 201 → Add `status_code=201` to `@router.post`.
    - TC-3.6 fails → `StartJobRequest` needs `ConfigDict(extra='forbid')`.
    - TC-3.8 fails (depth unchanged) → multi-request must be in SAME `async with client as c:` block.
    - Event loop errors → ensure `pytest-asyncio>=0.23.0` is installed.

    AVOID: Do NOT modify test file.
  </action>
  <verify>pytest tests/ -v --tb=short 2>&1 | tail -5</verify>
  <done>
    - `pytest tests/` → **29 passed, 0 failed** (Phase 1: 13 + Phase 2: 8 + Phase 3: 8)
    - Exit code: 0
  </done>
</task>

## Must-Haves

- [ ] `tests/test_phase3_endpoints.py` — 8 test functions, `httpx.AsyncClient` only
- [ ] TC-3.7 and TC-3.8 multi-request in same `async with` block

## Success Criteria

- [ ] `pytest tests/test_phase3_endpoints.py -v` → **8 passed, 0 failed**
- [ ] `pytest tests/` → **29 passed, 0 failed**
- [ ] Exit code: `0`
