---
phase: 6
plan: 2
wave: 2
gap_closure: false
---

# Plan 6.2: Async Service Layer — Real Payment Requests

## Objective

Refactor `app/services/job_service.py` and `app/repository/job_repo.py` to call the masumi SDK instead of generating mocked timestamps. Make `/start_job` async end-to-end.

## Context

- `app/services/job_service.py` — `create_job` is sync, 2-liner; must become `async`
- `app/repository/job_repo.py` — `create()` generates mock timestamps; must accept real values from SDK response
- `app/routers/jobs.py` — `start_job` route must become `async def`
- SDK call: `await payment.create_payment_request()` → `result["data"]` contains the fields

## SDK Response Shape

Based on the masumi SDK docs, `result["data"]` from `create_payment_request()` contains:

| Field in response | Maps to Job field |
|---|---|
| `blockchainIdentifier` | `blockchain_identifier` |
| `sellerVKey` | `seller_vkey` |
| `payByTime` | `pay_by_time` |
| `submitResultTime` | `submit_result_time` |
| `unlockTime` | `unlock_time` |

> If the response shape is slightly different (e.g. snake_case keys), the service falls back safely — see AVOID section.

## Tasks

<task type="auto">
  <name>Update app/repository/job_repo.py — create() signature</name>
  <files>app/repository/job_repo.py</files>
  <action>
    Change `create()` to accept the 5 blockchain values as explicit keyword args:

    ```python
    def create(
        self,
        input_hash: str,
        blockchain_identifier: str,
        pay_by_time: int,
        seller_vkey: str,
        submit_result_time: int,
        unlock_time: int,
    ) -> Job:
        job_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        job = Job(
            job_id=job_id,
            status=JobStatus.AWAITING_PAYMENT,
            input_hash=input_hash,
            blockchain_identifier=blockchain_identifier,
            created_at=now,
            updated_at=now,
            pay_by_time=pay_by_time,
            seller_vkey=seller_vkey,
            submit_result_time=submit_result_time,
            unlock_time=unlock_time,
        )
        with self._lock:
            self._store[job_id] = job
        return job
    ```

    Remove the `import time` — timestamps are no longer generated here.
  </action>
</task>

<task type="auto">
  <name>Update app/services/job_service.py</name>
  <files>app/services/job_service.py</files>
  <action>
    Replace `create_job` with an async version that calls the SDK:

    ```python
    from __future__ import annotations

    import uuid
    from typing import Optional

    from masumi import Payment

    from app.core.config import settings, masumi_config
    from app.domain.models import Job, JobStatus
    from app.repository.job_repo import InMemoryJobRepository


    async def create_job(repo: InMemoryJobRepository, input_hash: str) -> Job:
        """Call the masumi Payment SDK to get a real blockchain payment request."""
        payment = Payment(
            agent_identifier=settings.agent_identifier,
            config=masumi_config,
            network=settings.masumi_network,
            identifier_from_purchaser=uuid.uuid4().hex[:26],  # 26-char buyer hex
            input_data={"input_hash": input_hash},
        )
        result = await payment.create_payment_request()
        data = result["data"]

        return repo.create(
            input_hash=input_hash,
            blockchain_identifier=data["blockchainIdentifier"],
            pay_by_time=int(data["payByTime"]),
            seller_vkey=data["sellerVKey"],
            submit_result_time=int(data["submitResultTime"]),
            unlock_time=int(data["unlockTime"]),
        )


    def advance_job_state(
        repo: InMemoryJobRepository,
        job_id: str,
        target: JobStatus,
        result: Optional[str] = None,
        error: Optional[str] = None,
    ) -> Job:
        return repo.update_status(job_id, target, result=result, error=error)
    ```
  </action>
</task>

<task type="auto">
  <name>Update app/routers/jobs.py — make /start_job async</name>
  <files>app/routers/jobs.py</files>
  <action>
    Change `start_job` from `def` to `async def` and add `await`:

    ```python
    @router.post("/start_job", status_code=201, response_model=Job, response_model_by_alias=True)
    async def start_job(
        body: StartJobRequest,
        repo: InMemoryJobRepository = Depends(get_repo),
    ) -> Job:
        input_hash = hash_inputs(body.inputs)
        job = await job_service.create_job(repo, input_hash)
        return job
    ```

    All other routes remain unchanged (they don't call create_job).
  </action>
</task>

## Must-Haves

- [ ] `repo.create()` no longer generates mock timestamps — receives them as args
- [ ] `create_job` is `async` and `await`s `payment.create_payment_request()`
- [ ] `/start_job` route is `async def` and `await`s `job_service.create_job()`
- [ ] `advance_job_state` remains synchronous — no change needed

## AVOID

- Do NOT change `advance_job_state` signature.
- Do NOT import `time` in `job_repo.py` anymore.
- If the SDK response key names differ (e.g. snake_case instead of camelCase), wrap in a try/except and fall back to a safe mock — but DO NOT silently swallow errors in production paths.
