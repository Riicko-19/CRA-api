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
- [ ] `create()` returns `AWAITING_PAYMENT` job with `blockchain_identifier` starting with `"mock_bc_"`
- [ ] `get()` with unknown ID raises `JobNotFoundError`
- [ ] All tasks verified passing
