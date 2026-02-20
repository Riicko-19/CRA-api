---
phase: 1
plan: 1
wave: 1
gap_closure: false
---

# Plan 1.1: Domain Exceptions & Job Models

## Objective

Create the pure domain layer — custom exceptions and Pydantic v2 models with the `JobStatus` enum, `Job` model, `LEGAL_TRANSITIONS` map, and `validate_transition()` function. This is the foundation every other phase imports from. Zero I/O. Zero HTTP.

## Context

Load these files for context:
- `.gsd/SPEC.md`
- `.gsd/CONTEXT.md` → Sections: "Domain Models", "Job Lifecycle — State Machine", "Core Philosophy"

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

## Must-Haves

After all tasks complete, verify:
- [ ] `app/domain/__init__.py` exists (empty)
- [ ] `app/domain/exceptions.py` — 3 exception classes, zero imports
- [ ] `app/domain/models.py` — `JobStatus`, `Job`, `LEGAL_TRANSITIONS`, `validate_transition()`
- [ ] Zero imports from `fastapi`, `httpx`, or any I/O module across all 3 files

## Success Criteria

- [ ] `python -c "from app.domain.models import Job, JobStatus, LEGAL_TRANSITIONS, validate_transition"` exits 0
- [ ] All tasks verified passing
- [ ] No regressions in tests

---
---
phase: 1
plan: 2
wave: 2
gap_closure: false
---

# Plan 1.2: Phase 1 Test Suite

## Objective

Write and pass the complete Pytest verification suite for Phase 1. Every test case defined in `PHASE_1.md` must pass. This plan runs AFTER Plan 1.1 is complete — the domain layer must already exist.

## Context

Load these files for context:
- `.gsd/SPEC.md`
- `.gsd/PHASE_1.md` → "Verification Criteria" section
- `app/domain/models.py` (created in Plan 1.1)
- `app/domain/exceptions.py` (created in Plan 1.1)

## Tasks

<task type="auto">
  <name>Create tests/test_phase1_models.py</name>
  <files>tests/__init__.py, tests/test_phase1_models.py</files>
  <action>
    1. Create `tests/__init__.py` as an empty file (if it doesn't exist).
    2. Create `tests/test_phase1_models.py` with ALL 6 test cases below. Do NOT paraphrase — implement them exactly as specified:

    ```python
    import pytest
    from datetime import datetime
    from pydantic import ValidationError

    from app.domain.models import Job, JobStatus, validate_transition
    from app.domain.exceptions import InvalidStateTransitionError


    # --- Helpers ---

    def _make_valid_job(**overrides) -> Job:
        """Factory for a valid Job instance."""
        defaults = dict(
            job_id="test-job-id-0001",
            status=JobStatus.AWAITING_PAYMENT,
            input_hash="a" * 64,
            blockchain_identifier="mock_bc_test",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        defaults.update(overrides)
        return Job(**defaults)


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
                EXTRA_FIELD="should_fail",
            )


    # TC-1.3: Job model is frozen (immutable)
    def test_job_is_frozen():
        job = _make_valid_job()
        with pytest.raises(ValidationError):
            job.status = JobStatus.RUNNING


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
            pytest.fail("Expected InvalidStateTransitionError")
        except InvalidStateTransitionError as e:
            assert e.from_state == "completed"
            assert e.to_state == "running"
    ```

    AVOID:
    - Do NOT use `monkeypatch`, `mocker`, or any fixture that touches the filesystem or network.
    - Do NOT alter the parametrize argument lists — TC-1.5 must cover ALL 6 illegal pairs.
    - The `_make_valid_job` helper MUST default `input_hash` to exactly 64 characters.
  </action>
  <verify>pytest tests/test_phase1_models.py -v</verify>
  <done>
    - `pytest tests/test_phase1_models.py -v` outputs exactly:
      - `test_job_status_members` PASSED
      - `test_job_rejects_extra_fields` PASSED
      - `test_job_is_frozen` PASSED
      - `test_legal_transitions[...][3 parametrize cases]` ALL PASSED
      - `test_illegal_transitions[...][6 parametrize cases]` ALL PASSED
      - `test_invalid_transition_error_attributes` PASSED
    - Final line: `6 passed` (parametrized cases counted as sub-items of 6 test functions)
    - Exit code: 0
    - Zero warnings about missing imports or unresolved references.
  </done>
</task>

<task type="auto">
  <name>Install dependencies and run gate check</name>
  <files>requirements.txt</files>
  <action>
    1. Check if `requirements.txt` exists. If not, create it with:
    ```
    fastapi>=0.110.0
    pydantic>=2.0.0
    httpx>=0.27.0
    pytest>=8.0.0
    pytest-asyncio>=0.23.0
    uvicorn>=0.29.0
    ```
    2. Run: `pip install -r requirements.txt`
    3. Run the gate: `pytest tests/test_phase1_models.py -v`
    4. If any test fails — debug and fix `app/domain/models.py` or `app/domain/exceptions.py` (NOT the test file) until all 6 pass.

    AVOID:
    - Do NOT edit the test file to make tests pass — fix the implementation.
    - Do NOT downgrade pydantic below v2.
    - Do NOT add `pytest-mock` or `anyio` unless a clear import error requires it.
  </action>
  <verify>pytest tests/test_phase1_models.py -v --tb=short 2>&1 | tail -5</verify>
  <done>
    - `pytest tests/test_phase1_models.py` → 6 passed, 0 failed, exit code 0.
    - No imports from `fastapi`, `httpx`, or any I/O module exist in `app/domain/`.
  </done>
</task>

## Must-Haves

After all tasks complete, verify:
- [ ] `tests/__init__.py` exists (empty)
- [ ] `tests/test_phase1_models.py` contains all 6 test functions with exact parametrize pairs
- [ ] `requirements.txt` exists with pinned major versions

## Success Criteria

- [ ] `pytest tests/test_phase1_models.py -v` → **6 passed, 0 failed**
- [ ] Exit code: `0`
- [ ] All tasks verified passing
- [ ] No regressions in tests
