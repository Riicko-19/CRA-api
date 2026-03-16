---
phase: 8
plan: 4
wave: 3
gap_closure: false
---

# Plan 8.4: Test Suite Updates

## Objective

Update `tests/test_phase4_full_flow.py` so that all 8 test cases remain green after the
router changes in Plan 8.3. The key behavioural change is:

- `POST /provide_input` now returns `"status": "running"` (not `"completed"`).
- The background task (`execute_agent_task`) reaches COMPLETED **asynchronously** —
  it is never awaited during an HTTP request.
- Tests must either:
  a) **Poll** `/status/{job_id}` until `completed`, **or**
  b) **Directly invoke** `execute_agent_task(job_id, repo)` after the POST.

The chosen strategy is **(b) — direct invocation** via a conftest fixture that patches
`asyncio.sleep` and exposes a helper. This keeps tests fast (no real 5-second wait) and
deterministic (no polling loops with timeouts).

Also add a new **TC-8.1** test that verifies the 429 rate-limit response.

## Context

### Tests that will break after Plan 8.3

| Test | What breaks |
|---|---|
| `test_provide_input_valid_signature` | asserts `status == "completed"` — now `"running"` |
| `test_full_job_lifecycle` | asserts `final["status"] == "completed"` — now `"running"` |

All other tests are un-affected.

### Fix strategy

1. Add a `mock_agent_sleep` autouse fixture to `conftest.py` that patches
   `app.services.agent_runner.asyncio.sleep` with `AsyncMock(return_value=None)` — so
   the sleep resolves instantly when directly awaited.
2. In the two affected tests, after the `/provide_input` POST, directly `await` the
   background task:
   ```python
   await execute_agent_task(job_id, repo)
   ```
3. Then assert `status == "completed"`.

The `repo` is accessible via `app.state.repo` (same app instance used by the test client).

## Tasks

<task type="auto">
  <name>Add mock_agent_sleep autouse fixture to tests/conftest.py</name>
  <files>tests/conftest.py</files>
  <action>
    Add the following import additions and new fixture **after** the existing
    `mock_qdrant_client` fixture.

    New import line (add to the existing `from unittest.mock import ...` line):
    ```python
    from unittest.mock import AsyncMock, MagicMock, patch   # AsyncMock already present
    ```
    (no change needed — AsyncMock and patch already imported)

    New fixture at the bottom of the file:

    ```python
    @pytest.fixture(autouse=True)
    def mock_agent_sleep():
        """Patch asyncio.sleep inside agent_runner for ALL tests.

        Prevents any real 5-second pause when execute_agent_task is invoked
        directly inside a test.
        """
        with patch(
            "app.services.agent_runner.asyncio.sleep",
            new_callable=AsyncMock,
        ) as mock:
            yield mock
    ```
  </action>
  <verify>pytest tests/ -v --tb=short 2>&1 | findstr /C:"passed" /C:"failed"</verify>
</task>

<task type="auto">
  <name>Update test_phase4_full_flow.py</name>
  <files>tests/test_phase4_full_flow.py</files>
  <action>
    Replace the entire file with:

    ```python
    import pytest
    import httpx

    from app.main import create_app
    from app.services.agent_runner import execute_agent_task


    @pytest.fixture
    def app():
        return create_app()


    @pytest.fixture
    def client(app):
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


    # TC-4.3: POST /provide_input with valid signature → job is RUNNING immediately,
    #          then COMPLETED after the background task runs.
    @pytest.mark.asyncio
    async def test_provide_input_valid_signature(client, app):
        async with client as c:
            job = await _create_job(c)
            job_id = job["job_id"]
            r = await c.post("/provide_input", json={
                "job_id": job_id,
                "signature": f"valid_sig_{job_id}",
                "data": {"confirmation": "payment_received"},
            })
        # Endpoint returns RUNNING (background task not yet complete)
        assert r.status_code == 200
        assert r.json()["status"] == "running"

        # Directly invoke the background task (asyncio.sleep is mocked to no-op)
        repo = app.state.repo
        await execute_agent_task(job_id, repo)

        # Now the job should be COMPLETED
        completed_job = repo.get(job_id)
        assert completed_job.status == "completed"
        assert completed_job.result is not None


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


    # TC-4.8: Full lifecycle — awaiting_payment → running (via provide_input)
    #          → completed (via direct background task invocation)
    @pytest.mark.asyncio
    async def test_full_job_lifecycle(client, app):
        async with client as c:
            job = await _create_job(c)
            assert job["status"] == "awaiting_payment"
            job_id = job["job_id"]

            r = await c.post("/provide_input", json={
                "job_id": job_id,
                "signature": f"valid_sig_{job_id}",
                "data": {"confirm": True},
            })
            # Immediate response is RUNNING
            assert r.json()["status"] == "running"

        # Run the background task
        repo = app.state.repo
        await execute_agent_task(job_id, repo)

        # Verify via status endpoint
        async with client as c:
            status_r = await c.get(f"/status/{job_id}")
        assert status_r.json()["status"] == "completed"


    # TC-8.1: /start_job respects 5/minute rate limit — 6th request gets 429
    @pytest.mark.asyncio
    async def test_start_job_rate_limit(client):
        async with client as c:
            for _ in range(5):
                r = await c.post("/start_job", json={"inputs": {"task": "t"}})
                assert r.status_code == 201
            r = await c.post("/start_job", json={"inputs": {"task": "t"}})
        assert r.status_code == 429
    ```

    KEY POINTS:
    - The `app` fixture is extracted separately so both `client` and individual tests can
      share the same app instance (needed to access `app.state.repo`).
    - `test_provide_input_valid_signature` and `test_full_job_lifecycle` now directly
      `await execute_agent_task(job_id, repo)` after the HTTP call. The `mock_agent_sleep`
      conftest fixture ensures `asyncio.sleep(5)` resolves instantly.
    - TC-8.1 makes 6 POST requests in rapid succession inside a single `AsyncClient`
      context (same IP). The 6th must return 429.
  </action>
  <verify>pytest tests/test_phase4_full_flow.py -v --tb=short</verify>
</task>

## Must-Haves

- [ ] `mock_agent_sleep` autouse fixture in `conftest.py` patches `app.services.agent_runner.asyncio.sleep`
- [ ] `test_provide_input_valid_signature` asserts `status == "running"` before direct task invocation, then `"completed"` on the repo object
- [ ] `test_full_job_lifecycle` asserts `status == "running"` from HTTP response, then `"completed"` after direct task invocation
- [ ] TC-8.1 `test_start_job_rate_limit` verifies 429 on 6th request
- [ ] `pytest tests/ -v` — all tests pass (≥50 + 1 new = ≥51)

## Success Criteria

- `pytest tests/ -v --tb=short` → all tests pass, no failures
- `pytest tests/test_phase4_full_flow.py::test_start_job_rate_limit -v` → PASSED
