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
        r = await c.post("/start_job", json={"inputs": {"task": "do_work"}})
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


# TC-3.8: Multiple /start_job calls each return a unique job_id
@pytest.mark.asyncio
async def test_multiple_jobs_have_unique_ids(client):
    async with client as c:
        r1 = await c.post("/start_job", json={"inputs": {"task": "x"}})
        r2 = await c.post("/start_job", json={"inputs": {"task": "x"}})
    assert r1.json()["job_id"] != r2.json()["job_id"]
