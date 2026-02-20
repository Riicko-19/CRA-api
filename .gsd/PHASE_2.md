# PHASE 2 — In-Memory Repository

## Status: [ ] PENDING

## Prerequisites
- Phase 1 COMPLETE (`pytest tests/test_phase1_models.py` → all green)

## Context Reference
Read `CONTEXT.md` → Sections: "Architecture", "Job Lifecycle — State Machine", "Error Handling"

---

## Scope

Create the persistence layer using a thread-safe in-memory dictionary.
**No HTTP layer yet.** Pure Python + domain models only.

```
app/
├── domain/               ← already exists (Phase 1)
├── repository/
│   ├── __init__.py       (empty)
│   └── job_repo.py       (InMemoryJobRepository)
└── services/
    ├── __init__.py       (empty)
    └── job_service.py    (create_job, advance_job_state)
```

---

## Implementation Directives

### `app/repository/job_repo.py`

```python
import threading
import uuid
from datetime import datetime, timezone
from typing import Optional
from app.domain.models import Job, JobStatus, LEGAL_TRANSITIONS, validate_transition
from app.domain.exceptions import JobNotFoundError, InvalidStateTransitionError

class InMemoryJobRepository:
    def __init__(self):
        self._store: dict[str, Job] = {}
        self._lock = threading.Lock()

    def create(self, input_hash: str) -> Job:
        """Creates a new job in AWAITING_PAYMENT state. Thread-safe."""
        ...

    def get(self, job_id: str) -> Job:
        """Returns Job or raises JobNotFoundError. Thread-safe."""
        ...

    def update_status(self, job_id: str, target: JobStatus,
                      result: Optional[str] = None,
                      error: Optional[str] = None) -> Job:
        """
        Validates transition via validate_transition(), then returns a NEW
        frozen Job instance (model_copy or reconstruct — do NOT mutate).
        Thread-safe via _lock.
        Raises: JobNotFoundError, InvalidStateTransitionError
        """
        ...

    def count(self) -> int:
        """Returns number of jobs in store. Thread-safe."""
        ...
```

**Critical constraints:**
- `Job` is frozen — you MUST create a new instance on every state change.
  Use `job.model_copy(update={...})` (Pydantic v2) or reconstruct explicitly.
- `_lock` MUST wrap every read AND write to `_store`.
- `blockchain_identifier` = `"mock_bc_" + job_id[:8]`
- `job_id` = `str(uuid.uuid4())`
- All `datetime` values = `datetime.now(timezone.utc)`

### `app/services/job_service.py`
Two pure functions that wrap the repo:

```python
def create_job(repo: InMemoryJobRepository, input_hash: str) -> Job:
    return repo.create(input_hash)

def advance_job_state(repo: InMemoryJobRepository, job_id: str,
                      target: JobStatus,
                      result: str | None = None,
                      error: str | None = None) -> Job:
    return repo.update_status(job_id, target, result=result, error=error)
```

---

## Verification Criteria (Pytest — ALL must pass)

Create `tests/test_phase2_repository.py`.

```python
import threading

# TC-2.1: create() returns a job in AWAITING_PAYMENT state
def test_create_job_initial_state():
    repo = InMemoryJobRepository()
    job = repo.create(input_hash="a" * 64)
    assert job.status == JobStatus.AWAITING_PAYMENT
    assert job.input_hash == "a" * 64
    assert job.blockchain_identifier.startswith("mock_bc_")
    assert job.result is None
    assert job.error is None

# TC-2.2: get() returns the same job that was created
def test_get_returns_created_job():
    repo = InMemoryJobRepository()
    job = repo.create(input_hash="b" * 64)
    retrieved = repo.get(job.job_id)
    assert retrieved.job_id == job.job_id

# TC-2.3: get() raises JobNotFoundError for unknown ID
def test_get_unknown_job_raises():
    repo = InMemoryJobRepository()
    with pytest.raises(JobNotFoundError):
        repo.get("nonexistent-id")

# TC-2.4: Legal state transition updates status and updated_at
def test_legal_transition_updates_job():
    repo = InMemoryJobRepository()
    job = repo.create(input_hash="c" * 64)
    updated = repo.update_status(job.job_id, JobStatus.RUNNING)
    assert updated.status == JobStatus.RUNNING
    assert updated.updated_at >= job.updated_at

# TC-2.5: Illegal state transition raises InvalidStateTransitionError
def test_illegal_transition_raises():
    repo = InMemoryJobRepository()
    job = repo.create(input_hash="d" * 64)
    with pytest.raises(InvalidStateTransitionError):
        repo.update_status(job.job_id, JobStatus.COMPLETED)  # skip RUNNING

# TC-2.6: count() reflects stored jobs
def test_count_reflects_stored_jobs():
    repo = InMemoryJobRepository()
    assert repo.count() == 0
    repo.create("e" * 64)
    repo.create("f" * 64)
    assert repo.count() == 2

# TC-2.7: Thread-safety — concurrent creates produce unique IDs
def test_concurrent_creates_are_unique():
    repo = InMemoryJobRepository()
    ids = []
    def worker():
        job = repo.create("g" * 64)
        ids.append(job.job_id)
    threads = [threading.Thread(target=worker) for _ in range(100)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert len(set(ids)) == 100  # all unique

# TC-2.8: completed job with result is stored correctly
def test_completed_job_stores_result():
    repo = InMemoryJobRepository()
    job = repo.create("h" * 64)
    repo.update_status(job.job_id, JobStatus.RUNNING)
    done = repo.update_status(job.job_id, JobStatus.COMPLETED, result="output_data")
    assert done.status == JobStatus.COMPLETED
    assert done.result == "output_data"
    assert done.error is None
```

## ✅ Definition of COMPLETE
- `pytest tests/test_phase2_repository.py` → **8/8 PASSED, 0 FAILED**
- No FastAPI imports in `repository/` or `services/`.
- `Job` is never mutated in-place anywhere.
