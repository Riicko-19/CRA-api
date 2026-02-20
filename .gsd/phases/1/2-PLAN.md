---
phase: 1
plan: 2
wave: 2
---

# Plan 1.2: Phase 1 Test Suite

## Objective

Write and pass the complete Pytest verification suite for Phase 1. Every test case defined in `PHASE_1.md` must pass. This plan runs AFTER Plan 1.1 is complete — the domain layer must already exist.

## Context

- `.gsd/SPEC.md`
- `.gsd/PHASE_1.md` → "Verification Criteria" section
- `app/domain/models.py` (created in Plan 1.1)
- `app/domain/exceptions.py` (created in Plan 1.1)

---

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
  <files>requirements.txt (if missing)</files>
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

## Success Criteria

- [ ] `tests/__init__.py` exists (empty)
- [ ] `tests/test_phase1_models.py` contains all 6 test functions with exact parametrize pairs
- [ ] `pytest tests/test_phase1_models.py -v` → **6 passed, 0 failed**
- [ ] Exit code: `0`
- [ ] `requirements.txt` exists with pinned major versions
