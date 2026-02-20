---
phase: 2
plan: 3
wave: 2
gap_closure: false
---

# Plan 2.3: Phase 2 Test Suite

## Objective

Write and pass the complete Pytest verification suite for Phase 2. All 8 test cases from `PHASE_2.md` must pass, including the thread-safety concurrent test. This plan runs AFTER Plans 2.1 and 2.2 are complete.

## Context

Load these files for context:
- `.gsd/PHASE_2.md` → "Verification Criteria" section
- `app/repository/job_repo.py`
- `app/services/job_service.py`

## Tasks

<task type="auto">
  <name>Create tests/test_phase2_repository.py</name>
  <files>tests/test_phase2_repository.py</files>
  <action>
    Create `tests/test_phase2_repository.py` with ALL 8 test cases below. Implement exactly as specified:

    ```python
    import threading
    import pytest

    from app.domain.models import JobStatus
    from app.domain.exceptions import JobNotFoundError, InvalidStateTransitionError
    from app.repository.job_repo import InMemoryJobRepository


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
        lock = threading.Lock()

        def worker():
            job = repo.create("g" * 64)
            with lock:
                ids.append(job.job_id)

        threads = [threading.Thread(target=worker) for _ in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(ids) == 100
        assert len(set(ids)) == 100  # all unique


    # TC-2.8: completed job with result is stored correctly
    def test_completed_job_stores_result():
        repo = InMemoryJobRepository()
        job = repo.create("h" * 64)
        repo.update_status(job.job_id, JobStatus.RUNNING)
        done = repo.update_status(
            job.job_id, JobStatus.COMPLETED, result="output_data"
        )
        assert done.status == JobStatus.COMPLETED
        assert done.result == "output_data"
        assert done.error is None
    ```

    AVOID:
    - Do NOT use `monkeypatch`, network calls, or filesystem access.
    - Do NOT share `repo` instances between tests — each test creates its own fresh `InMemoryJobRepository()`.
    - TC-2.7 MUST spawn exactly 100 threads and assert both `len(ids) == 100` AND `len(set(ids)) == 100`.
  </action>
  <verify>pytest tests/test_phase2_repository.py -v</verify>
  <done>
    - `pytest tests/test_phase2_repository.py -v` shows all 8 tests PASSED.
    - Exit code: 0.
    - TC-2.7 (thread safety) passes reliably (no flakiness at 100 threads).
  </done>
</task>

<task type="auto">
  <name>Run full Phase 2 pytest gate</name>
  <files>(no new files — verification only)</files>
  <action>
    Run the gate command:
    ```
    pytest tests/test_phase2_repository.py -v --tb=short
    ```

    If any test fails:
    - Fix `app/repository/job_repo.py` or `app/services/job_service.py` (NOT the test file).
    - Common failure causes:
      - TC-2.4 fails: `updated_at` not being updated → ensure `model_copy` sets `updated_at` to `datetime.now(timezone.utc)`.
      - TC-2.5 fails: transition not guarded → ensure `validate_transition()` is called inside `update_status`.
      - TC-2.7 fails (non-unique IDs): `_lock` not wrapping `_store[job_id] = job` → check `create()` lock scope.
      - TC-2.8 fails: `result` not stored → ensure `model_copy(update={"result": result, ...})` includes result field.

    AVOID:
    - Do NOT modify test file to bypass failures.
    - Do NOT use `time.sleep()` in the thread test — it should pass without artificial delays.
  </action>
  <verify>pytest tests/test_phase2_repository.py -v --tb=short 2>&1 | tail -5</verify>
  <done>
    - `pytest tests/test_phase2_repository.py` → **8 passed, 0 failed**, exit code 0.
    - `pytest tests/` (Phase 1 + Phase 2) → **21 passed, 0 failed**.
  </done>
</task>

## Must-Haves

- [ ] `tests/test_phase2_repository.py` contains all 8 test functions
- [ ] Each test uses a fresh `InMemoryJobRepository()` — no shared state
- [ ] TC-2.7 spawns exactly 100 threads

## Success Criteria

- [ ] `pytest tests/test_phase2_repository.py -v` → **8 passed, 0 failed**
- [ ] `pytest tests/` → **21 passed, 0 failed** (Phase 1 + 2 combined)
- [ ] Exit code: `0`
