# PHASE 3 — Core Endpoints & Hashing

## Status: [ ] PENDING

## Prerequisites
- Phase 1 COMPLETE
- Phase 2 COMPLETE

## Context Reference
Read `CONTEXT.md` → Sections: "Endpoints Contract", "Hashing Contract", "Error Handling"

---

## Scope

Wire the FastAPI application and implement the first 3 endpoints.
Introduce the deterministic SHA-256 hashing utility.

```
app/
├── domain/           ← Phase 1
├── repository/       ← Phase 2
├── services/         ← Phase 2
├── utils/
│   ├── __init__.py   (empty)
│   └── hashing.py    (hash_inputs)
├── routers/
│   ├── __init__.py   (empty)
│   └── jobs.py       (/availability, /input_schema, /start_job)
├── schemas/
│   ├── __init__.py   (empty)
│   └── requests.py   (StartJobRequest)
└── main.py           (FastAPI app factory)
```

---

## Implementation Directives

### `app/utils/hashing.py`
```python
import hashlib, json

def hash_inputs(payload: dict) -> str:
    """
    Deterministic SHA-256 of a dict.
    sort_keys=True ensures field order independence.
    separators=(',', ':') eliminates whitespace variation.
    """
    canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()
```

No external dependencies. `hashlib` and `json` are stdlib only.

### `app/schemas/requests.py`
```python
from pydantic import BaseModel, ConfigDict
from typing import Any

class StartJobRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    inputs: dict[str, Any]
```

### `app/routers/jobs.py`

```python
# GET /availability
# Returns: {"available": true, "queue_depth": <int>}
# Never returns non-200.

# GET /input_schema
# Returns a static hardcoded JSON Schema dict describing valid `inputs`.
# Example: {"type": "object", "properties": {"task": {"type": "string"}}, "required": ["task"]}

# POST /start_job
# - Body: StartJobRequest
# - Hash inputs via hash_inputs()
# - Call job_service.create_job(repo, input_hash)
# - Return 201 with Job model
```

### `app/main.py`
```python
from fastapi import FastAPI
from app.repository.job_repo import InMemoryJobRepository
from app.routers import jobs

def create_app() -> FastAPI:
    app = FastAPI(title="Masumi MIP-003 Gateway", version="1.0.0")
    repo = InMemoryJobRepository()
    app.include_router(jobs.router)
    # Attach repo to app.state so routers can access it via Request
    app.state.repo = repo
    return app

app = create_app()
```

**Dependency injection pattern for repo:**
```python
# In routers/jobs.py
from fastapi import Request

def get_repo(request: Request) -> InMemoryJobRepository:
    return request.app.state.repo
```
Use `Depends(get_repo)` in each endpoint.

---

## Verification Criteria (Pytest — ALL must pass)

Create `tests/test_phase3_endpoints.py`.
**Use `httpx.AsyncClient` with `ASGITransport` for all HTTP tests.**

```python
import pytest, hashlib, json
import httpx
from app.main import create_app

@pytest.fixture
def client():
    app = create_app()
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")

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
    r = await client.get("/availability")
    assert r.status_code == 200
    data = r.json()
    assert data["available"] is True
    assert isinstance(data["queue_depth"], int)

# TC-3.4: GET /input_schema returns 200 with a JSON Schema object
@pytest.mark.asyncio
async def test_input_schema(client):
    r = await client.get("/input_schema")
    assert r.status_code == 200
    schema = r.json()
    assert schema["type"] == "object"
    assert "properties" in schema

# TC-3.5: POST /start_job creates a job and returns 201
@pytest.mark.asyncio
async def test_start_job_creates_job(client):
    r = await client.post("/start_job", json={"inputs": {"task": "do_work"}})
    assert r.status_code == 201
    job = r.json()
    assert job["status"] == "awaiting_payment"
    assert len(job["input_hash"]) == 64
    assert job["blockchain_identifier"].startswith("mock_bc_")

# TC-3.6: POST /start_job with extra top-level fields returns 422
@pytest.mark.asyncio
async def test_start_job_rejects_extra_fields(client):
    r = await client.post("/start_job", json={"inputs": {"task": "x"}, "hacker_field": "evil"})
    assert r.status_code == 422

# TC-3.7: POST /start_job is deterministic — same inputs produce same hash
@pytest.mark.asyncio
async def test_start_job_hash_determinism(client):
    payload = {"inputs": {"b": 2, "a": 1}}
    r1 = await client.post("/start_job", json=payload)
    r2 = await client.post("/start_job", json=payload)
    assert r1.json()["input_hash"] == r2.json()["input_hash"]

# TC-3.8: queue_depth increases after job creation
@pytest.mark.asyncio
async def test_queue_depth_increases(client):
    before = (await client.get("/availability")).json()["queue_depth"]
    await client.post("/start_job", json={"inputs": {"task": "x"}})
    after = (await client.get("/availability")).json()["queue_depth"]
    assert after == before + 1
```

## ✅ Definition of COMPLETE
- `pytest tests/test_phase3_endpoints.py` → **8/8 PASSED, 0 FAILED**
- `hash_inputs` uses only stdlib (`hashlib`, `json`). Zero external deps.
- Repo is injected via `app.state`, never instantiated inside a route handler.
