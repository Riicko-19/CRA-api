# PHASE 1 — Domain Models & State Machine

## Status: [ ] PENDING

## Context Reference
Read `CONTEXT.md` → Sections: "Domain Models", "Job Lifecycle — State Machine", "Core Philosophy"

---

## Scope

Create the pure domain layer. No I/O. No HTTP. No DB.
This phase produces exactly **3 files**:

```
app/
├── domain/
│   ├── __init__.py          (empty)
│   ├── models.py            (Pydantic v2 models)
│   └── exceptions.py        (custom exception classes)
```

---

## Implementation Directives

### `app/domain/exceptions.py`
Define these custom exceptions (plain Python, no Pydantic):

```python
class JobNotFoundError(Exception):
    def __init__(self, job_id: str):
        self.job_id = job_id
        super().__init__(f"Job {job_id!r} not found")

class InvalidStateTransitionError(Exception):
    def __init__(self, from_state: str, to_state: str):
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(f"Cannot transition from '{from_state}' to '{to_state}'")

class InvalidSignatureError(Exception):
    pass
```

### `app/domain/models.py`
- Import: `from pydantic import BaseModel, ConfigDict`, `from enum import Enum`, `from datetime import datetime`, `from typing import Optional`
- **ALL models MUST use `model_config = ConfigDict(extra='forbid', frozen=True)`**
- Define `JobStatus(str, Enum)` with values: `awaiting_payment`, `running`, `completed`, `failed`
- Define `Job(BaseModel)` with fields per `CONTEXT.md`
- Define `LEGAL_TRANSITIONS: dict[JobStatus, list[JobStatus]]`:

```python
LEGAL_TRANSITIONS = {
    JobStatus.AWAITING_PAYMENT: [JobStatus.RUNNING],
    JobStatus.RUNNING: [JobStatus.COMPLETED, JobStatus.FAILED],
    JobStatus.COMPLETED: [],
    JobStatus.FAILED: [],
}
```

- Define a pure function `validate_transition(current: JobStatus, target: JobStatus) -> None` that raises `InvalidStateTransitionError` if `target not in LEGAL_TRANSITIONS[current]`.

---

## Verification Criteria (Pytest — ALL must pass)

Create `tests/test_phase1_models.py`.

```python
# TC-1.1: JobStatus has exactly 4 members
def test_job_status_members():
    assert set(JobStatus) == {
        JobStatus.AWAITING_PAYMENT,
        JobStatus.RUNNING,
        JobStatus.COMPLETED,
        JobStatus.FAILED,
    }

# TC-1.2: Job model rejects extra fields
def test_job_rejects_extra_fields():
    with pytest.raises(ValidationError):
        Job(
            job_id="abc",
            status=JobStatus.AWAITING_PAYMENT,
            input_hash="x" * 64,
            blockchain_identifier="mock_bc_abc",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            EXTRA_FIELD="should_fail",  # must trigger ValidationError
        )

# TC-1.3: Job model is frozen (immutable)
def test_job_is_frozen():
    job = Job(...)  # valid Job instance
    with pytest.raises(ValidationError):
        job.status = JobStatus.RUNNING  # mutation must fail

# TC-1.4: Legal transitions do not raise
@pytest.mark.parametrize("from_s,to_s", [
    (JobStatus.AWAITING_PAYMENT, JobStatus.RUNNING),
    (JobStatus.RUNNING, JobStatus.COMPLETED),
    (JobStatus.RUNNING, JobStatus.FAILED),
])
def test_legal_transitions(from_s, to_s):
    validate_transition(from_s, to_s)  # must NOT raise

# TC-1.5: Illegal transitions raise InvalidStateTransitionError
@pytest.mark.parametrize("from_s,to_s", [
    (JobStatus.AWAITING_PAYMENT, JobStatus.COMPLETED),
    (JobStatus.AWAITING_PAYMENT, JobStatus.FAILED),
    (JobStatus.COMPLETED, JobStatus.RUNNING),
    (JobStatus.FAILED, JobStatus.RUNNING),
    (JobStatus.COMPLETED, JobStatus.AWAITING_PAYMENT),
    (JobStatus.RUNNING, JobStatus.AWAITING_PAYMENT),
])
def test_illegal_transitions(from_s, to_s):
    with pytest.raises(InvalidStateTransitionError):
        validate_transition(from_s, to_s)

# TC-1.6: InvalidStateTransitionError carries state info
def test_invalid_transition_error_attributes():
    try:
        validate_transition(JobStatus.COMPLETED, JobStatus.RUNNING)
    except InvalidStateTransitionError as e:
        assert e.from_state == "completed"
        assert e.to_state == "running"
```

## ✅ Definition of COMPLETE
- `pytest tests/test_phase1_models.py` → **6/6 PASSED, 0 FAILED**
- No imports from `fastapi`, `httpx`, or any I/O module in this phase's files.
