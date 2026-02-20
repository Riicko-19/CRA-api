---
phase: 3
plan: 3
wave: 2
gap_closure: false
---

# Plan 3.3: Phase 3 Test Suite

## Objective

Write and pass the complete Pytest verification suite for Phase 3. All 8 test cases from `PHASE_3.md` must pass. Uses `httpx.AsyncClient` with `ASGITransport` for all HTTP tests. Runs AFTER Plans 3.1 and 3.2 are complete.

## Context

Load these files for context:
- `.gsd/PHASE_3.md` → "Verification Criteria" section
- `app/main.py` (Plan 3.2)
- `app/utils/hashing.py` (Plan 3.1)

## Tasks

<task type="auto">
  <name>Create tests/test_phase3_endpoints.py</name>
  <files>tests/test_phase3_endpoints.py</files>
  <action>
    Create `tests/test_phase3_endpoints.py` with ALL 8 test cases below exactly as specified:

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

    NOTES on `client` fixture usage:
    - The `client` fixture returns an `httpx.AsyncClient` that must be used as an async context manager (`async with client as c`). This handles lifespan events correctly with ASGI.
    - Each test that uses `client` opens its own async context — this ensures proper connection cleanup.
    - TC-3.7 and TC-3.8 keep the same `async with client as c` block open across multiple requests so they share the SAME app state (same repo instance).

    AVOID:
    - Do NOT use `@pytest.fixture(scope="session")` — each test needs `create_app()` for a fresh repo.
    - Do NOT use `TestClient` (sync) from `starlette.testclient` — must use `httpx.AsyncClient`.
    - Do NOT add `event_loop` fixture or `asyncio_mode` config — `pytest-asyncio` handles this with `@pytest.mark.asyncio`.
    - Do NOT modify any implementation file to make tests pass — fix implementation only.
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

    If Phase 3 tests fail, debug in this order:
    - TC-3.3/3.4/3.5/3.6/3.7/3.8 fail with `RuntimeError: no running event loop`:
      → Ensure `pytest-asyncio>=0.23.0` is installed and `@pytest.mark.asyncio` is on each async test.
    - TC-3.3 fails with 404:
      → Check that `app.include_router(jobs.router)` is in `create_app()`.
    - TC-3.5 fails with 200 instead of 201:
      → Add `status_code=201` to `@router.post("/start_job", status_code=201)`.
    - TC-3.6 fails (422 not raised):
      → Confirm `StartJobRequest` has `ConfigDict(extra='forbid')`.
    - TC-3.4 fails (`"type"` not `"object"`):
      → `StartJobRequest.model_json_schema()` on a model with one dict field — check the returned schema structure. The top-level key should be `"type": "object"`. If not present, return `{"type": "object", "properties": StartJobRequest.model_json_schema().get("properties", {})}`.
    - TC-3.8 fails (queue_depth doesn't change):
      → TC-3.8 multi-request must be under SAME `async with client as c:` block.

    AVOID: Do NOT modify test file. Fix implementation only.
  </action>
  <verify>pytest tests/ -v --tb=short 2>&1 | tail -5</verify>
  <done>
    - `pytest tests/` → **29 passed, 0 failed** (Phase 1: 13 + Phase 2: 8 + Phase 3: 8)
    - Exit code: 0
  </done>
</task>

## Must-Haves

- [ ] `tests/test_phase3_endpoints.py` — all 8 test functions
- [ ] `client` fixture returns `httpx.AsyncClient` with `ASGITransport` — NOT `TestClient`
- [ ] TC-3.7 and TC-3.8 make multiple requests inside the SAME `async with client as c:` block

## Success Criteria

- [ ] `pytest tests/test_phase3_endpoints.py -v` → **8 passed, 0 failed**
- [ ] `pytest tests/` → **29 passed, 0 failed**
- [ ] Exit code: `0`
