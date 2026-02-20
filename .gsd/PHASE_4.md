# PHASE 4 — Status, Input & Error Handling

## Status: [ ] PENDING

## Prerequisites
- Phase 1, 2, 3 ALL COMPLETE

## Context Reference
Read `CONTEXT.md` → Sections: "Endpoints Contract", "Error Handling", "Job Lifecycle"

---

## Scope

Complete the API surface: `/status`, `/provide_input`, mock signature verification,
and the global exception handler. This is the final integration phase.

```
app/
├── routers/
│   └── jobs.py          ← ADD: /status/{job_id}, /provide_input
├── schemas/
│   └── requests.py      ← ADD: ProvideInputRequest
├── utils/
│   └── signatures.py    ← NEW: verify_signature (mock Ed25519)
└── main.py              ← ADD: global exception handlers
```

---

## Implementation Directives

### `app/schemas/requests.py` (extend Phase 3 file)
```python
class ProvideInputRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    job_id: str
    signature: str
    data: dict[str, Any]
```

### `app/utils/signatures.py`
```python
from app.domain.exceptions import InvalidSignatureError

def verify_signature(job_id: str, signature: str) -> None:
    """
    Mock Ed25519 verification.
    A real implementation would use cryptography.hazmat.
    Contract: signature MUST equal "valid_sig_" + job_id
    Raises InvalidSignatureError on mismatch.
    """
    expected = f"valid_sig_{job_id}"
    if signature != expected:
        raise InvalidSignatureError(f"Signature mismatch for job {job_id!r}")
```

### `app/routers/jobs.py` (extend Phase 3 file)

```python
# GET /status/{job_id}
# - Calls repo.get(job_id)
# - Returns Job (200) or raises JobNotFoundError → caught by global handler → 404

# POST /provide_input
# - Body: ProvideInputRequest
# - Step 1: repo.get(job_id) → 404 if missing
# - Step 2: verify_signature(job_id, signature) → 403 if invalid
# - Step 3: advance_job_state(repo, job_id, RUNNING) [AWAITING_PAYMENT → RUNNING]
# - Step 4: advance_job_state(repo, job_id, COMPLETED, result="Task executed successfully")
# - Returns updated Job (200)
```

### `app/main.py` — Global Exception Handlers

Add these handlers to the FastAPI app in `create_app()`:

```python
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.domain.exceptions import JobNotFoundError, InvalidStateTransitionError, InvalidSignatureError

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
```

---

## Verification Criteria (Pytest — ALL must pass)

Create `tests/test_phase4_full_flow.py`.

```python
import pytest
import httpx
from app.main import create_app
from app.domain.models import JobStatus

@pytest.fixture
def client():
    app = create_app()
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")

async def _create_job(client) -> dict:
    r = await client.post("/start_job", json={"inputs": {"task": "test_task"}})
    assert r.status_code == 201
    return r.json()

# TC-4.1: GET /status/{job_id} returns the correct job
@pytest.mark.asyncio
async def test_get_status_returns_job(client):
    job = await _create_job(client)
    r = await client.get(f"/status/{job['job_id']}")
    assert r.status_code == 200
    assert r.json()["job_id"] == job["job_id"]

# TC-4.2: GET /status with unknown ID returns 404
@pytest.mark.asyncio
async def test_get_status_unknown_job(client):
    r = await client.get("/status/nonexistent-000")
    assert r.status_code == 404
    assert "not found" in r.json()["detail"].lower()

# TC-4.3: POST /provide_input with valid signature completes the job
@pytest.mark.asyncio
async def test_provide_input_valid_signature(client):
    job = await _create_job(client)
    job_id = job["job_id"]
    r = await client.post("/provide_input", json={
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
    job = await _create_job(client)
    r = await client.post("/provide_input", json={
        "job_id": job["job_id"],
        "signature": "wrong_signature",
        "data": {},
    })
    assert r.status_code == 403

# TC-4.5: POST /provide_input for unknown job returns 404
@pytest.mark.asyncio
async def test_provide_input_unknown_job(client):
    r = await client.post("/provide_input", json={
        "job_id": "ghost-job-id",
        "signature": "valid_sig_ghost-job-id",
        "data": {},
    })
    assert r.status_code == 404

# TC-4.6: POST /provide_input with extra fields returns 422
@pytest.mark.asyncio
async def test_provide_input_rejects_extra_fields(client):
    job = await _create_job(client)
    r = await client.post("/provide_input", json={
        "job_id": job["job_id"],
        "signature": f"valid_sig_{job['job_id']}",
        "data": {},
        "evil_extra": "hacked",
    })
    assert r.status_code == 422

# TC-4.7: 422 response body is JSON with "detail" key
@pytest.mark.asyncio
async def test_422_response_shape(client):
    r = await client.post("/start_job", json={"bad_field": "no_inputs"})
    assert r.status_code == 422
    body = r.json()
    assert "detail" in body

# TC-4.8: Full lifecycle — awaiting_payment → running → completed
@pytest.mark.asyncio
async def test_full_job_lifecycle(client):
    # Create
    job = await _create_job(client)
    assert job["status"] == "awaiting_payment"
    job_id = job["job_id"]

    # Provide input (triggers full completion)
    r = await client.post("/provide_input", json={
        "job_id": job_id,
        "signature": f"valid_sig_{job_id}",
        "data": {"confirm": True},
    })
    final = r.json()
    assert final["status"] == "completed"

    # Status check reflects final state
    status_r = await client.get(f"/status/{job_id}")
    assert status_r.json()["status"] == "completed"
```

## ✅ Definition of COMPLETE
- `pytest tests/test_phase4_full_flow.py` → **8/8 PASSED, 0 FAILED**
- `pytest tests/` (all phases together) → **30/30 PASSED, 0 FAILED**
- No hardcoded job states or IDs anywhere in handler code.
- All error responses use the global exception handlers — no inline `HTTPException` for domain errors.
