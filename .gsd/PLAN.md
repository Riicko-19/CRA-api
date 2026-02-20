---
phase: 2
plan: 1
wave: 1
gap_closure: false
---

# Plan 2.1: InMemoryJobRepository

## Objective

Build the thread-safe, in-memory persistence layer. This is the only component allowed to own `Job` storage. It enforces the state machine strictly — no caller can bypass `validate_transition()`. No HTTP, no FastAPI, no I/O.

## Context

Load these files for context:
- `.gsd/SPEC.md`
- `.gsd/CONTEXT.md` → Sections: "Architecture", "Job Lifecycle — State Machine"
- `app/domain/models.py` — Job, JobStatus, LEGAL_TRANSITIONS, validate_transition
- `app/domain/exceptions.py` — JobNotFoundError, InvalidStateTransitionError

## Tasks

<task type="auto">
  <name>Create app/repository/__init__.py (empty)</name>
  <files>app/repository/__init__.py</files>
  <action>
    Create `app/repository/__init__.py` as a completely empty file.
    No content, no imports, no comments.
  </action>
  <verify>python -c "import app.repository; print('OK')"</verify>
  <done>
    - `app/repository/__init__.py` exists and is empty.
    - `import app.repository` exits 0.
  </done>
</task>

<task type="auto">
  <name>Create app/repository/job_repo.py</name>
  <files>app/repository/job_repo.py</files>
  <action>
    Create `app/repository/job_repo.py` with the following implementation exactly:

    **Imports (ONLY these):**
    ```python
    import threading
    import uuid
    from datetime import datetime, timezone
    from typing import Optional

    from app.domain.models import Job, JobStatus, validate_transition
    from app.domain.exceptions import JobNotFoundError
    ```

    **Class:**
    ```python
    class InMemoryJobRepository:
        def __init__(self):
            self._store: dict[str, Job] = {}
            self._lock = threading.Lock()

        def create(self, input_hash: str) -> Job:
            job_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            job = Job(
                job_id=job_id,
                status=JobStatus.AWAITING_PAYMENT,
                input_hash=input_hash,
                blockchain_identifier="mock_bc_" + job_id[:8],
                created_at=now,
                updated_at=now,
            )
            with self._lock:
                self._store[job_id] = job
            return job

        def get(self, job_id: str) -> Job:
            with self._lock:
                job = self._store.get(job_id)
            if job is None:
                raise JobNotFoundError(job_id)
            return job

        def update_status(
            self,
            job_id: str,
            target: JobStatus,
            result: Optional[str] = None,
            error: Optional[str] = None,
        ) -> Job:
            with self._lock:
                job = self._store.get(job_id)
                if job is None:
                    raise JobNotFoundError(job_id)
                validate_transition(job.status, target)
                updated = job.model_copy(update={
                    "status": target,
                    "updated_at": datetime.now(timezone.utc),
                    "result": result,
                    "error": error,
                })
                self._store[job_id] = updated
            return updated

        def count(self) -> int:
            with self._lock:
                return len(self._store)
    ```

    AVOID:
    - Do NOT mutate `job` directly — `Job` is frozen. Always use `model_copy(update={...})`.
    - Do NOT release `_lock` between the `get` and `update` inside `update_status` — the entire read-validate-write sequence MUST be atomic under the same lock acquisition.
    - Do NOT import `fastapi`, `httpx`, or any HTTP module.
    - Do NOT call `validate_transition()` outside of `_lock` in `update_status`.
    - `datetime.now(timezone.utc)` — always use timezone-aware datetimes (NOT `datetime.utcnow()`).
  </action>
  <verify>python -c "from app.repository.job_repo import InMemoryJobRepository; r = InMemoryJobRepository(); j = r.create('a'*64); print('repo OK', j.status)"</verify>
  <done>
    - `app/repository/job_repo.py` imports cleanly.
    - `InMemoryJobRepository().create('a'*64)` returns a `Job` with `status == JobStatus.AWAITING_PAYMENT`.
    - `InMemoryJobRepository().get('nonexistent')` raises `JobNotFoundError`.
    - No imports from `fastapi`, `httpx`, or any I/O module.
  </done>
</task>

## Must-Haves

- [ ] `app/repository/__init__.py` exists (empty)
- [ ] `app/repository/job_repo.py` — `InMemoryJobRepository` with `create`, `get`, `update_status`, `count`
- [ ] `_lock` wraps every `_store` access (reads AND writes)
- [ ] `Job` is never mutated — always `model_copy(update={...})`
- [ ] `update_status` is fully atomic (get + validate + write under single lock)

## Success Criteria

- [ ] `python -c "from app.repository.job_repo import InMemoryJobRepository"` exits 0
- [ ] All tasks verified passing

---
---
phase: 2
plan: 2
wave: 1
gap_closure: false
---

# Plan 2.2: Service Layer

## Objective

Create the thin service wrapper layer — pure functions that delegate to the repository. Nothing stateful here. No HTTP. This layer is the calling convention used by routers in Phase 3+.

## Context

Load these files for context:
- `.gsd/SPEC.md`
- `app/domain/models.py`
- `app/repository/job_repo.py`

## Tasks

<task type="auto">
  <name>Create app/services/__init__.py (empty)</name>
  <files>app/services/__init__.py</files>
  <action>
    Create `app/services/__init__.py` as a completely empty file.
    No content, no imports, no comments.
  </action>
  <verify>python -c "import app.services; print('OK')"</verify>
  <done>
    - `app/services/__init__.py` exists and is empty.
  </done>
</task>

<task type="auto">
  <name>Create app/services/job_service.py</name>
  <files>app/services/job_service.py</files>
  <action>
    Create `app/services/job_service.py` with exactly these two pure functions:

    **Imports (ONLY these):**
    ```python
    from typing import Optional

    from app.domain.models import Job, JobStatus
    from app.repository.job_repo import InMemoryJobRepository
    ```

    **Functions:**
    ```python
    def create_job(repo: InMemoryJobRepository, input_hash: str) -> Job:
        return repo.create(input_hash)


    def advance_job_state(
        repo: InMemoryJobRepository,
        job_id: str,
        target: JobStatus,
        result: Optional[str] = None,
        error: Optional[str] = None,
    ) -> Job:
        return repo.update_status(job_id, target, result=result, error=error)
    ```

    AVOID:
    - Do NOT add any business logic here — pure pass-throughs to the repo.
    - Do NOT import `fastapi`, `httpx`, or any HTTP module.
    - Do NOT use `str | None` union syntax — use `Optional[str]`.
  </action>
  <verify>python -c "from app.services.job_service import create_job, advance_job_state; print('service OK')"</verify>
  <done>
    - `app/services/job_service.py` imports cleanly.
    - `create_job` and `advance_job_state` are importable.
  </done>
</task>

## Must-Haves

- [ ] `app/services/__init__.py` exists (empty)
- [ ] `app/services/job_service.py` — `create_job`, `advance_job_state` (pure functions, no state)
- [ ] No business logic — delegates 100% to repo

## Success Criteria

- [ ] `python -c "from app.services.job_service import create_job, advance_job_state"` exits 0
- [ ] All tasks verified passing

---
---
phase: 2
plan: 3
wave: 2
gap_closure: false
---

# Plan 2.3: Phase 2 Test Suite

## Objective

Write and pass the complete Pytest verification suite for Phase 2. All 8 test cases must pass, including the thread-safety concurrent test. Runs AFTER Plans 2.1 and 2.2 are complete.

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
    Create `tests/test_phase2_repository.py` with ALL 8 test cases below exactly as specified:

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
    - Each test creates its own fresh `InMemoryJobRepository()` — no shared state.
    - TC-2.7 MUST spawn exactly 100 threads.
    - Do NOT modify test file to fix failures — fix the implementation instead.
  </action>
  <verify>pytest tests/test_phase2_repository.py -v</verify>
  <done>
    - `pytest tests/test_phase2_repository.py -v` → 8 passed, 0 failed, exit code 0.
    - TC-2.7 passes reliably.
  </done>
</task>

<task type="auto">
  <name>Run combined Phase 1 + Phase 2 gate check</name>
  <files>(no new files)</files>
  <action>
    Run: `pytest tests/ -v --tb=short`

    If Phase 2 tests fail, fix `app/repository/job_repo.py` or `app/services/job_service.py`:
    - TC-2.4 failure → `updated_at` not refreshed: ensure `model_copy` sets `"updated_at": datetime.now(timezone.utc)`
    - TC-2.5 failure → transition not guarded: ensure `validate_transition()` is inside `update_status`
    - TC-2.7 failure (duplicate IDs) → lock scope too narrow: ensure `_store[job_id] = job` is inside `with self._lock`
    - TC-2.8 failure → result not persisted: ensure `model_copy(update={..., "result": result})`

    AVOID: Do NOT modify test files. Fix implementation only.
  </action>
  <verify>pytest tests/ -v --tb=short 2>&1 | tail -3</verify>
  <done>
    - `pytest tests/` → **21 passed, 0 failed** (Phase 1: 13 + Phase 2: 8)
    - Exit code: 0
  </done>
</task>

## Must-Haves

- [ ] `tests/test_phase2_repository.py` — all 8 test functions, each with fresh repo
- [ ] TC-2.7 spawns exactly 100 threads

## Success Criteria

- [ ] `pytest tests/test_phase2_repository.py -v` → **8 passed, 0 failed**
- [ ] `pytest tests/` → **21 passed, 0 failed**
- [ ] Exit code: `0`
