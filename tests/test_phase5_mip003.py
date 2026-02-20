import time
import pytest
import httpx

from app.domain.models import JobStatus, validate_transition
from app.domain.exceptions import InvalidStateTransitionError
from app.main import create_app


@pytest.fixture
def client():
    app = create_app()
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    )


async def _create_job(c: httpx.AsyncClient) -> dict:
    r = await c.post("/start_job", json={"inputs": {"task": "mip003_test"}})
    assert r.status_code == 201
    return r.json()


# TC-5.1: JobStatus has 5 members including awaiting_input
def test_job_status_has_awaiting_input():
    assert len(JobStatus) == 5
    assert JobStatus.AWAITING_INPUT.value == "awaiting_input"


# TC-5.2: RUNNING -> AWAITING_INPUT and AWAITING_INPUT -> RUNNING are legal
def test_running_awaiting_input_roundtrip():
    validate_transition(JobStatus.RUNNING, JobStatus.AWAITING_INPUT)   # no raise
    validate_transition(JobStatus.AWAITING_INPUT, JobStatus.RUNNING)   # no raise


# TC-5.3: AWAITING_INPUT -> COMPLETED and AWAITING_INPUT -> FAILED are illegal
@pytest.mark.parametrize("target", [JobStatus.COMPLETED, JobStatus.FAILED])
def test_awaiting_input_cannot_skip_to_terminal(target):
    with pytest.raises(InvalidStateTransitionError):
        validate_transition(JobStatus.AWAITING_INPUT, target)


# TC-5.4: GET /availability returns MIP-003 contract
@pytest.mark.asyncio
async def test_availability_mip003_shape(client):
    async with client as c:
        r = await c.get("/availability")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "available"
    assert body["service_type"] == "masumi-agent"


# TC-5.5: POST /start_job response has blockchainIdentifier (camelCase)
@pytest.mark.asyncio
async def test_start_job_has_blockchain_identifier_camel(client):
    async with client as c:
        job = await _create_job(c)
    assert "blockchainIdentifier" in job
    assert job["blockchainIdentifier"].startswith("mock_bc_")


# TC-5.6: POST /start_job response has all four MIP-003 fields
@pytest.mark.asyncio
async def test_start_job_has_mip003_fields(client):
    async with client as c:
        job = await _create_job(c)
    assert "payByTime" in job
    assert "sellerVKey" in job
    assert "submitResultTime" in job
    assert "unlockTime" in job
    assert isinstance(job["payByTime"], int)
    assert isinstance(job["submitResultTime"], int)
    assert isinstance(job["unlockTime"], int)
    assert isinstance(job["sellerVKey"], str)


# TC-5.7: payByTime < submitResultTime < unlockTime (future, ordered timestamps)
@pytest.mark.asyncio
async def test_pay_by_time_is_future(client):
    now = int(time.time())
    async with client as c:
        job = await _create_job(c)
    assert job["payByTime"] > now
    assert job["submitResultTime"] > job["payByTime"]
    assert job["unlockTime"] > job["submitResultTime"]


# TC-5.8: Smoke — all critical imports and model config is clean
def test_phase5_imports_cleanly():
    from app.domain.models import Job, JobStatus, LEGAL_TRANSITIONS
    from app.repository.job_repo import InMemoryJobRepository
    from app.routers.jobs import router
    from app.main import create_app
    assert len(JobStatus) == 5
    assert JobStatus.AWAITING_INPUT in LEGAL_TRANSITIONS
    assert Job.model_config["populate_by_name"] is True
