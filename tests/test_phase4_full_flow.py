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
#          then the background task runs (synchronously in ASGI test transport)
#          and moves it to COMPLETED.
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
    # Endpoint returns RUNNING state immediately
    assert r.status_code == 200
    assert r.json()["status"] == "running"

    # httpx ASGI transport runs BackgroundTasks synchronously after the response.
    # By the time the `async with` block exits, the background job is COMPLETED.
    completed_job = app.state.repo.get(job_id)
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


# TC-4.8: Full lifecycle — awaiting_payment → running (HTTP response)
#          → completed (background task runs synchronously in test transport)
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
        # Immediate HTTP response is RUNNING
        assert r.json()["status"] == "running"

    # After the async-with block exits, background task has already completed
    # (httpx ASGI transport is synchronous for BackgroundTasks).
    assert app.state.repo.get(job_id).status == "completed"


# TC-8.1: /start_job respects 5/minute rate limit — 6th request gets 429
@pytest.mark.asyncio
async def test_start_job_rate_limit(client):
    async with client as c:
        for _ in range(5):
            r = await c.post("/start_job", json={"inputs": {"task": "t"}})
            assert r.status_code == 201
        r = await c.post("/start_job", json={"inputs": {"task": "t"}})
    assert r.status_code == 429
