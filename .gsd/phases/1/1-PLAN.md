---
phase: 1
plan: 1
wave: 1
---

# Plan 1.1: Domain Exceptions & Job Models

## Objective

Create the pure domain layer — custom exceptions and Pydantic v2 models with the `JobStatus` enum, `Job` model, `LEGAL_TRANSITIONS` map, and `validate_transition()` function. This is the foundation every other phase imports from. Zero I/O. Zero HTTP.

## Context

- `.gsd/SPEC.md`
- `.gsd/CONTEXT.md` → Sections: "Domain Models", "Job Lifecycle — State Machine", "Core Philosophy"

---

## Tasks

<task type="auto">
  <name>Create app/domain/exceptions.py</name>
  <files>app/domain/__init__.py, app/domain/exceptions.py</files>
  <action>
    1. Create `app/domain/__init__.py` as an empty file.
    2. Create `app/domain/exceptions.py` with exactly these three exception classes — no Pydantic, no imports beyond builtins:

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

    AVOID:
    - Do NOT import anything (no pydantic, no fastapi, no stdlib).
    - Do NOT add extra methods or attributes beyond what is shown.
    - The `__init__` signatures must match EXACTLY — used by tests via `e.from_state`, `e.to_state`, `e.job_id`.
  </action>
  <verify>python -c "from app.domain.exceptions import JobNotFoundError, InvalidStateTransitionError, InvalidSignatureError; print('OK')"</verify>
  <done>
    - `app/domain/__init__.py` exists and is empty.
    - `app/domain/exceptions.py` imports cleanly with zero errors.
    - `JobNotFoundError("x").job_id == "x"` is True.
    - `InvalidStateTransitionError("a","b").from_state == "a"` is True.
    - `InvalidStateTransitionError("a","b").to_state == "b"` is True.
  </done>
</task>

<task type="auto">
  <name>Create app/domain/models.py</name>
  <files>app/domain/models.py</files>
  <action>
    Create `app/domain/models.py` with the following — in this exact order:

    **Imports (ONLY these):**
    ```python
    from __future__ import annotations
    from datetime import datetime
    from enum import Enum
    from typing import Optional
    from pydantic import BaseModel, ConfigDict
    from app.domain.exceptions import InvalidStateTransitionError
    ```

    **1. JobStatus enum:**
    ```python
    class JobStatus(str, Enum):
        AWAITING_PAYMENT = "awaiting_payment"
        RUNNING = "running"
        COMPLETED = "completed"
        FAILED = "failed"
    ```

    **2. Job model (Pydantic v2):**
    ```python
    class Job(BaseModel):
        model_config = ConfigDict(extra='forbid', frozen=True)

        job_id: str
        status: JobStatus
        input_hash: str
        blockchain_identifier: str
        created_at: datetime
        updated_at: datetime
        result: Optional[str] = None
        error: Optional[str] = None
    ```

    **3. Legal transitions map:**
    ```python
    LEGAL_TRANSITIONS: dict[JobStatus, list[JobStatus]] = {
        JobStatus.AWAITING_PAYMENT: [JobStatus.RUNNING],
        JobStatus.RUNNING:          [JobStatus.COMPLETED, JobStatus.FAILED],
        JobStatus.COMPLETED:        [],
        JobStatus.FAILED:           [],
    }
    ```

    **4. Transition validator:**
    ```python
    def validate_transition(current: JobStatus, target: JobStatus) -> None:
        if target not in LEGAL_TRANSITIONS[current]:
            raise InvalidStateTransitionError(
                from_state=current.value,
                to_state=target.value,
            )
    ```

    AVOID:
    - Do NOT import `fastapi`, `httpx`, or any I/O module.
    - Do NOT use `model_config = ConfigDict(extra='allow')` — must be `'forbid'`.
    - Do NOT set `frozen=False` — immutability is required.
    - Do NOT use `model_validator` or `field_validator` here — pure structural definition only.
    - The `validate_transition` function must pass `.value` strings to `InvalidStateTransitionError` (not the enum member), so `e.from_state == "completed"` works in tests.
  </action>
  <verify>python -c "from app.domain.models import Job, JobStatus, LEGAL_TRANSITIONS, validate_transition; print('OK')"</verify>
  <done>
    - `app/domain/models.py` imports cleanly.
    - `JobStatus` has exactly 4 members.
    - `Job` model instantiates with all required fields.
    - `Job` rejects extra fields (raises `ValidationError`).
    - `Job` is frozen (mutation raises `ValidationError`).
    - `LEGAL_TRANSITIONS` has 4 keys.
    - `validate_transition(JobStatus.AWAITING_PAYMENT, JobStatus.RUNNING)` does NOT raise.
    - `validate_transition(JobStatus.COMPLETED, JobStatus.RUNNING)` raises `InvalidStateTransitionError`.
  </done>
</task>

## Success Criteria

- [ ] `app/domain/__init__.py` exists (empty)
- [ ] `app/domain/exceptions.py` — 3 exception classes, zero imports
- [ ] `app/domain/models.py` — `JobStatus`, `Job`, `LEGAL_TRANSITIONS`, `validate_transition()`
- [ ] Zero imports from `fastapi`, `httpx`, or any I/O module across all 3 files
- [ ] `python -c "from app.domain.models import Job, JobStatus, LEGAL_TRANSITIONS, validate_transition"` exits 0
