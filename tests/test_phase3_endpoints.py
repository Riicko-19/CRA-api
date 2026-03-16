import hashlib
import pytest
import httpx

from app.main import create_app
from app.core.config import settings


@pytest.fixture
def client():
    app = create_app()
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    )


def _headers() -> dict[str, str]:
    return {"X-API-Key": settings.api_key}


def _start_payload() -> dict:
    return {
        "target_domain": "https://example.com",
        "my_product_usp": "Fast onboarding with built-in automation",
        "ideal_customer_profile": "SMB teams needing simple growth workflows",
    }


# TC-3.1: hash_inputs is deterministic (field-order independent)
def test_hash_inputs_deterministic():
    from app.utils.hashing import hash_inputs
    h1 = hash_inputs("https://example.com", "usp", "icp")
    h2 = hash_inputs("https://example.com", "usp", "icp")
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex = 64 chars


# TC-3.2: hash_inputs produces correct SHA-256
def test_hash_inputs_correctness():
    from app.utils.hashing import hash_inputs
    expected_canonical = '{"ideal_customer_profile":"icp","my_product_usp":"usp","target_domain":"https://example.com"}'
    expected_hash = hashlib.sha256(expected_canonical.encode()).hexdigest()
    assert hash_inputs("https://example.com", "usp", "icp") == expected_hash


# TC-3.3: GET /availability returns MIP-003 contract shape
@pytest.mark.asyncio
async def test_availability(client):
    async with client as c:
        r = await c.get("/availability")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "available"
    assert data["service_type"] == "masumi-agent"


# TC-3.4: GET /input_schema returns 200 with a JSON Schema object
@pytest.mark.asyncio
async def test_input_schema(client):
    async with client as c:
        r = await c.get("/input_schema")
    assert r.status_code == 200
    schema = r.json()
    assert schema["type"] == "object"
    assert "properties" in schema


# TC-3.5: POST /start_job creates a job and returns 201 with MIP-003 fields
@pytest.mark.asyncio
async def test_start_job_creates_job(client):
    async with client as c:
        r = await c.post("/start_job", json=_start_payload(), headers=_headers())
    assert r.status_code == 201
    job = r.json()
    assert job["status"] == "awaiting_payment"
    assert len(job["input_hash"]) == 64
    assert job["blockchainIdentifier"].startswith("mock_bc_")
    assert isinstance(job["payByTime"], int)
    assert job["sellerVKey"].startswith("mock_vkey_")


# TC-3.6: POST /start_job with extra top-level fields returns 422
@pytest.mark.asyncio
async def test_start_job_rejects_extra_fields(client):
    async with client as c:
        r = await c.post(
            "/start_job",
            json={**_start_payload(), "hacker_field": "evil"},
            headers=_headers(),
        )
    assert r.status_code == 422


# TC-3.7: POST /start_job is deterministic — same inputs produce same hash
@pytest.mark.asyncio
async def test_start_job_hash_determinism(client):
    payload = _start_payload()
    async with client as c:
        r1 = await c.post("/start_job", json=payload, headers=_headers())
        r2 = await c.post("/start_job", json=payload, headers=_headers())
    assert r1.json()["input_hash"] == r2.json()["input_hash"]


# TC-3.8: Multiple /start_job calls each return a unique job_id
@pytest.mark.asyncio
async def test_multiple_jobs_have_unique_ids(client):
    async with client as c:
        r1 = await c.post("/start_job", json=_start_payload(), headers=_headers())
        r2 = await c.post("/start_job", json=_start_payload(), headers=_headers())
    assert r1.json()["job_id"] != r2.json()["job_id"]


@pytest.mark.asyncio
async def test_start_job_requires_api_key(client):
    async with client as c:
        r = await c.post("/start_job", json=_start_payload())
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_start_job_rejects_invalid_target_domain(client):
    payload = _start_payload()
    payload["target_domain"] = "not-a-url"
    async with client as c:
        r = await c.post("/start_job", json=payload, headers=_headers())
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_start_job_rejects_empty_usp(client):
    payload = _start_payload()
    payload["my_product_usp"] = ""
    async with client as c:
        r = await c.post("/start_job", json=payload, headers=_headers())
    assert r.status_code == 422
