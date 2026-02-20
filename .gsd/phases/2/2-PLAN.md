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
- `app/repository/job_repo.py` (created in Plan 2.1)

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
    - `import app.services` exits 0.
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
    - Do NOT add any business logic here — these are pure pass-throughs to the repo.
    - Do NOT import `fastapi`, `httpx`, or any HTTP module.
    - Do NOT add state (no module-level variables).
    - Do NOT use `str | None` union syntax — use `Optional[str]` for Python 3.10 compatibility.
  </action>
  <verify>python -c "from app.services.job_service import create_job, advance_job_state; print('service OK')"</verify>
  <done>
    - `app/services/job_service.py` imports cleanly.
    - `create_job` and `advance_job_state` are importable.
    - No imports from `fastapi`, `httpx`, or any I/O module.
  </done>
</task>

## Must-Haves

- [ ] `app/services/__init__.py` exists (empty)
- [ ] `app/services/job_service.py` — `create_job`, `advance_job_state` (pure functions, no state)
- [ ] No business logic in service layer — delegates 100% to repo
- [ ] No FastAPI/HTTP imports anywhere in `services/`

## Success Criteria

- [ ] `python -c "from app.services.job_service import create_job, advance_job_state"` exits 0
- [ ] All tasks verified passing
