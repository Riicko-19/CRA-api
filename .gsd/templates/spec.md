# CONTEXT.md — Masumi MIP-003 API Gateway (Master Spec)

## Project Identity

| Key | Value |
|-----|-------|
| Standard | Masumi MIP-003 |
| Registry | Suko (Sukosumi) |
| Runtime | Python 3.10+ |
| Framework | FastAPI (latest stable) |
| Validation | Pydantic v2 (`model_config = ConfigDict(extra='forbid')`) |
| Hashing | `hashlib` SHA-256 (stdlib only — no external crypto deps) |
| Persistence | In-Memory Repository (no DB in MVP) |
| Test Runner | Pytest + httpx `AsyncClient` |

---

## Core Philosophy (Non-Negotiable)

```
Strict      > Flexible
Predictable > Intelligent
Secure      > Fast
Deterministic > Dynamic
```

Every design decision MUST be evaluated against these axioms.
If a choice adds flexibility at the cost of strictness, reject it.

---

## Architecture

```
Request
  │
  ▼
FastAPI Router
  │   - /availability      (GET)
  │   - /input_schema      (GET)
  │   - /start_job         (POST)
  │   - /status/{job_id}   (GET)
  │   - /provide_input     (POST)
  │
  ▼
Service Layer (pure functions, no I/O side-effects)
  │   - create_job()
  │   - advance_state()
  │   - hash_inputs()
  │   - verify_signature()  [mock]
  │
  ▼
InMemoryJobRepository (thread-safe, Repository pattern)
  │   - _store: dict[str, Job]
  │   - _lock: threading.Lock
  │
  ▼
Domain Models (Pydantic v2, extra='forbid')
      Job, JobStatus, InputSchema, StartJobRequest, ProvideInputRequest
```

---

## Job Lifecycle — State Machine

```
                ┌─────────────────────┐
  POST /start_job │                     │
─────────────────►  awaiting_payment   │
                │                     │
                └────────┬────────────┘
                         │  payment confirmed (mock)
                         ▼
                ┌─────────────────────┐
                │       running       │
                └────────┬────────────┘
                         │  task execution completes
                    ┌────┴────┐
                    ▼         ▼
               completed    failed
```

**Legal Transitions Only:**
| From | To | Trigger |
|------|----|---------|
| `awaiting_payment` | `running` | Payment confirmed |
| `running` | `completed` | Task succeeds |
| `running` | `failed` | Task raises exception |

**Illegal Transitions (must raise `InvalidStateTransitionError`):**
- Any state → `awaiting_payment`
- `completed` → any
- `failed` → any
- `awaiting_payment` → `completed` (skipping `running`)

---

## Domain Models (Strict Definitions)

```python
# All models MUST use:
model_config = ConfigDict(extra='forbid', frozen=True)

class JobStatus(str, Enum):
    AWAITING_PAYMENT = "awaiting_payment"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class Job(BaseModel):
    job_id: str                    # UUID4 string
    status: JobStatus
    input_hash: str                # SHA-256 hex digest of canonical input JSON
    blockchain_identifier: str     # mock: "mock_bc_" + job_id[:8]
    created_at: datetime
    updated_at: datetime
    result: Optional[str] = None
    error: Optional[str] = None
```

---

## Hashing Contract (Deterministic)

Input hashing MUST be reproducible given the same inputs.

```python
import hashlib, json

def hash_inputs(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()
```

- `sort_keys=True` — field order must NOT affect the hash.
- `separators=(',', ':')` — no whitespace in canonical form.
- Input: raw dict from `StartJobRequest.inputs`.

---

## Endpoints Contract

### GET /availability
Returns `{"available": true, "queue_depth": <int>}`. Always 200.

### GET /input_schema
Returns a static JSON Schema object describing valid `inputs` for `/start_job`.

### POST /start_job
- Accepts `StartJobRequest(inputs: dict[str, Any])` 
- Validates with Pydantic (`extra='forbid'` on nested models where applicable)
- Computes `input_hash` via `hash_inputs()`
- Creates job in `AWAITING_PAYMENT` state
- Returns `Job` model (201)

### GET /status/{job_id}
- Returns current `Job` or 404 if not found.

### POST /provide_input
- Accepts `ProvideInputRequest(job_id: str, signature: str, data: dict)`
- Verifies mock Ed25519 signature: `signature == "valid_sig_" + job_id`
- Advances job from `AWAITING_PAYMENT` → `RUNNING` → `COMPLETED`
- Returns updated `Job`

---

## Error Handling

| Situation | HTTP Code | Detail |
|-----------|-----------|--------|
| Pydantic validation failure | 422 | JSON with field-level errors |
| Job not found | 404 | `{"detail": "Job {id} not found"}` |
| Illegal state transition | 409 | `{"detail": "Cannot transition from X to Y"}` |
| Invalid signature | 403 | `{"detail": "Invalid signature"}` |

Global FastAPI exception handler MUST catch `RequestValidationError` and return a clean 422 JSON response.

---

## Test Conventions

- All tests use `pytest` + `httpx.AsyncClient` with `ASGITransport`.
- Tests are STRICTLY isolated — each test creates its own fresh app/repo instance.
- No shared state between tests.
- Parametrize illegal transition tests exhaustively.
