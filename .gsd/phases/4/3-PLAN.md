---
phase: 4
plan: 3
wave: 2
gap_closure: false
---

# Plan 4.3: Phase 4 Test Suite

## Objective

Write and pass the complete Pytest verification suite for Phase 4. All 8 test cases from `PHASE_4.md` must pass. Uses `httpx.AsyncClient` with `ASGITransport`. Runs AFTER Plans 4.1 and 4.2 are complete.

## Context

Load these files for context:
- `.gsd/PHASE_4.md` → "Verification Criteria" section
- `app/main.py` (Plan 4.2)
- `app/routers/jobs.py` (Plan 4.2)
- `app/utils/signatures.py` (Plan 4.1)

## Tasks

<task type="auto">
  <name>Create tests/test_phase4_full_flow.py</name>
  <files>tests/test_phase4_full_flow.py</files>
  <action>
    Create `tests/test_phase4_full_flow.py` with ALL 8 test cases exactly as specified:

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
            # Create
            job = await _create_job(c)
            assert job["status"] == "awaiting_payment"
            job_id = job["job_id"]

            # Provide input (triggers full completion)
            r = await c.post("/provide_input", json={
                "job_id": job_id,
                "signature": f"valid_sig_{job_id}",
                "data": {"confirm": True},
            })
            final = r.json()
            assert final["status"] == "completed"

            # Status check reflects final state
            status_r = await c.get(f"/status/{job_id}")
            assert status_r.json()["status"] == "completed"
    ```

    KEY: All tests that make multiple requests within one logical flow go inside ONE `async with client as c:` block.
    `_create_job(c)` is a helper that takes an open client — it must be called INSIDE `async with client as c:`.

    AVOID:
    - Do NOT use `TestClient` — must be `httpx.AsyncClient`.
    - Do NOT share client state across tests — each test calls `create_app()` fresh.
    - Do NOT add `conftest.py` — the fixture is in-file.
    - Do NOT use `await _create_job(client)` with the fixture directly — always inside `async with client as c:` and pass `c` to the helper.
  </action>
  <verify>pytest tests/test_phase4_full_flow.py -v</verify>
  <done>
    - `pytest tests/test_phase4_full_flow.py -v` → 8 passed, 0 failed, exit code 0.
    - TC-4.2 response body has `"detail"` containing "not found".
    - TC-4.3 response has `"status": "completed"` and `"result"` is not null.
    - TC-4.8 full lifecycle completes end-to-end.
  </done>
</task>

<task type="auto">
  <name>Run combined Phase 1+2+3+4 gate check</name>
  <files>(no new files)</files>
  <action>
    Run: `pytest tests/ -v --tb=short`

    Common Phase 4 failure guides:
    - TC-4.2 gets 500 instead of 404:
      → `JobNotFoundError` handler not registered. Ensure `@app.exception_handler(JobNotFoundError)` is inside `create_app()`.
    - TC-4.4 gets 500 instead of 403:
      → `InvalidSignatureError` handler not registered. Same fix.
    - TC-4.2 "not found" assertion fails:
      → Check the `str(exc)` on `JobNotFoundError` — must contain "not found" (lowercase). Verify `app/domain/exceptions.py`.
    - TC-4.6 gets 200 instead of 422:
      → `ProvideInputRequest` missing `extra='forbid'`.
    - TC-4.3 `result` is None:
      → `advance_job_state(..., result="Task executed successfully")` not set — check the second call in `/provide_input`.
    - TC-4.8 fails on status check after provide_input:
      → TC-4.8 must run all requests inside ONE `async with client as c:` block so they share the same repo.
    - Phase 3 tests break:
      → `StartJobRequest` was accidentally removed from `requests.py`. Check both classes still present.

    AVOID: Do NOT modify test files. Fix implementation only.
  </action>
  <verify>pytest tests/ -v --tb=short 2>&1 | tail -5</verify>
  <done>
    - `pytest tests/` → **37 passed, 0 failed** (Phase 1: 13 + Phase 2: 8 + Phase 3: 8 + Phase 4: 8)
    - Exit code: 0
  </done>
</task>

## Must-Haves

- [ ] `tests/test_phase4_full_flow.py` — 8 test functions, `httpx.AsyncClient` only
- [ ] `_create_job(c)` helper takes an OPEN client — called inside `async with client as c:`
- [ ] TC-4.8 makes all 3 requests inside ONE `async with client as c:` block

## Success Criteria

- [ ] `pytest tests/test_phase4_full_flow.py -v` → **8 passed, 0 failed**
- [ ] `pytest tests/` → **37 passed, 0 failed**
- [ ] Exit code: `0`
