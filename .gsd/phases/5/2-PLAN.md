---
phase: 5
plan: 2
wave: 1
gap_closure: false
---

# Plan 5.2: Availability Endpoint & Repository Mock Fields

## Objective

Change the `/availability` response to the MIP-003 contract and update `InMemoryJobRepository.create()` to populate the four new MIP-003 timestamp/key fields on every `Job`.

## Context

- `app/routers/jobs.py` (Phase 4 — 5 existing routes)
- `app/repository/job_repo.py` (Phase 2 — `create()` builds `Job`)
- `app/domain/models.py` (Plan 5.1 — `Job` now has 4 new required fields)

## Tasks

<task type="auto">
  <name>Change /availability response in app/routers/jobs.py</name>
  <files>app/routers/jobs.py</files>
  <action>
    In `app/routers/jobs.py`, replace the `/availability` handler only.

    FIND:
    ```python
    @router.get("/availability")
    def availability(repo: InMemoryJobRepository = Depends(get_repo)):
        return {"available": True, "queue_depth": repo.count()}
    ```

    REPLACE WITH:
    ```python
    @router.get("/availability")
    def availability():
        return {"status": "available", "service_type": "masumi-agent"}
    ```

    AVOID:
    - Do NOT touch any other route.
    - The `repo` dependency is removed — no argument needed for this route now.
    - Do NOT remove the `Depends` import — other routes still use it.
  </action>
  <verify>python -c "from app.routers.jobs import router; r=[x for x in router.routes if x.path=='/availability'][0]; print('availability route OK', r.path)"</verify>
  <done>
    - `GET /availability` handler takes no `repo` parameter.
    - All other routes unchanged.
  </done>
</task>

<task type="auto">
  <name>Update InMemoryJobRepository.create() in app/repository/job_repo.py</name>
  <files>app/repository/job_repo.py</files>
  <action>
    Replace `app/repository/job_repo.py` with this complete implementation:

    ```python
    import threading
    import time
    import uuid
    from datetime import datetime, timezone
    from typing import Optional

    from app.domain.models import Job, JobStatus, validate_transition
    from app.domain.exceptions import JobNotFoundError


    class InMemoryJobRepository:
        def __init__(self):
            self._store: dict[str, Job] = {}
            self._lock = threading.Lock()

        def create(self, input_hash: str) -> Job:
            job_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            now_ts = int(time.time())
            job = Job(
                job_id=job_id,
                status=JobStatus.AWAITING_PAYMENT,
                input_hash=input_hash,
                blockchain_identifier="mock_bc_" + job_id[:8],
                created_at=now,
                updated_at=now,
                pay_by_time=now_ts + 3600,
                seller_vkey="mock_vkey_" + job_id[:8],
                submit_result_time=now_ts + 7200,
                unlock_time=now_ts + 86400,
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

    KEY POINTS:
    - `pay_by_time`, `seller_vkey`, `submit_result_time`, `unlock_time` — passed by Python name (works because `populate_by_name=True`).
    - `blockchain_identifier` — also passed by Python name for the same reason.
    - `import time` added at top.
    - All other logic (threading, locking, `update_status`, `count`) is unchanged.

    AVOID:
    - Do NOT use alias names (`blockchainIdentifier`) when constructing — use snake_case Python names.
    - Do NOT change `update_status` logic — it still uses `model_copy`.
  </action>
  <verify>python -c "from app.repository.job_repo import InMemoryJobRepository; repo=InMemoryJobRepository(); job=repo.create('a'*64); print('pay_by_time:', job.pay_by_time, 'seller_vkey:', job.seller_vkey); assert job.pay_by_time > 0; print('repo OK')"</verify>
  <done>
    - `repo.create()` returns a `Job` with non-zero `pay_by_time`, `seller_vkey`, `submit_result_time`, `unlock_time`.
    - `job.pay_by_time > int(time.time())` (future timestamp).
    - All Phase 2 logic preserved.
  </done>
</task>

## Must-Haves

- [ ] `GET /availability` → `{"status": "available", "service_type": "masumi-agent"}` — no `repo` arg
- [ ] `repo.create()` populates all 4 MIP-003 fields with sensible mock values
- [ ] `pay_by_time = now_ts + 3600`, `submit_result_time = now_ts + 7200`, `unlock_time = now_ts + 86400`
- [ ] `seller_vkey = "mock_vkey_" + job_id[:8]`

## Success Criteria

- [ ] `GET /availability` returns `{"status": "available", "service_type": "masumi-agent"}`
- [ ] `repo.create("x"*64).pay_by_time > 0`
- [ ] `repo.create("x"*64).seller_vkey.startswith("mock_vkey_")`
