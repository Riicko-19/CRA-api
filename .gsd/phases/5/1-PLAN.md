---
phase: 5
plan: 1
wave: 1
gap_closure: false
---

# Plan 5.1: Domain Model — AWAITING_INPUT + MIP-003 Job Fields

## Objective

Add the `AWAITING_INPUT` lifecycle state and four MIP-003 blockchain fields to the `Job` model. Pure domain layer — no HTTP, no FastAPI.

## Context

- `app/domain/models.py` (Phase 1 — `JobStatus`, `Job`, `LEGAL_TRANSITIONS`)

## Tasks

<task type="auto">
  <name>Update app/domain/models.py</name>
  <files>app/domain/models.py</files>
  <action>
    Replace `app/domain/models.py` with this complete implementation:

    ```python
    from __future__ import annotations

    import time
    from datetime import datetime
    from enum import Enum
    from typing import Optional

    from pydantic import BaseModel, ConfigDict, Field

    from app.domain.exceptions import InvalidStateTransitionError


    class JobStatus(str, Enum):
        AWAITING_PAYMENT = "awaiting_payment"
        AWAITING_INPUT   = "awaiting_input"
        RUNNING          = "running"
        COMPLETED        = "completed"
        FAILED           = "failed"


    class Job(BaseModel):
        model_config = ConfigDict(
            extra="forbid",
            frozen=True,
            populate_by_name=True,
        )

        job_id: str
        status: JobStatus
        input_hash: str
        blockchain_identifier: str = Field(alias="blockchainIdentifier")
        created_at: datetime
        updated_at: datetime
        result: Optional[str] = None
        error: Optional[str] = None

        # MIP-003 blockchain fields
        pay_by_time: int         = Field(alias="payByTime")
        seller_vkey: str         = Field(alias="sellerVKey")
        submit_result_time: int  = Field(alias="submitResultTime")
        unlock_time: int         = Field(alias="unlockTime")


    LEGAL_TRANSITIONS: dict[JobStatus, list[JobStatus]] = {
        JobStatus.AWAITING_PAYMENT: [JobStatus.RUNNING],
        JobStatus.RUNNING:          [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.AWAITING_INPUT],
        JobStatus.AWAITING_INPUT:   [JobStatus.RUNNING],
        JobStatus.COMPLETED:        [],
        JobStatus.FAILED:           [],
    }


    def validate_transition(current: JobStatus, target: JobStatus) -> None:
        if target not in LEGAL_TRANSITIONS[current]:
            raise InvalidStateTransitionError(
                from_state=current.value,
                to_state=target.value,
            )
    ```

    KEY POINTS:
    - `blockchain_identifier` NOW has `Field(alias="blockchainIdentifier")` — JSON output will use camelCase.
    - `populate_by_name=True` — allows constructing Job with either `blockchain_identifier=...` OR `blockchainIdentifier=...`.
    - All 4 MIP-003 fields are required (no defaults) — `job_repo.py` must always supply them.
    - `AWAITING_INPUT` sits between `RUNNING` and back to `RUNNING` — not a terminal state.

    AVOID:
    - Do NOT make the 4 MIP-003 fields Optional — they are always required.
    - Do NOT change the `frozen=True` or `extra="forbid"` settings.
    - Do NOT rename `blockchain_identifier` — only add the alias.
    - `time` import is not used in this file — remove it. Use plain `int` types only.
  </action>
  <verify>python -c "from app.domain.models import JobStatus, Job, LEGAL_TRANSITIONS; print('members:', [s.value for s in JobStatus]); assert JobStatus.AWAITING_INPUT in LEGAL_TRANSITIONS; print('transitions OK')"</verify>
  <done>
    - `JobStatus` has 5 members including `awaiting_input`.
    - `LEGAL_TRANSITIONS[RUNNING]` includes `AWAITING_INPUT`.
    - `LEGAL_TRANSITIONS[AWAITING_INPUT]` is `[RUNNING]`.
    - `Job` has fields `pay_by_time`, `seller_vkey`, `submit_result_time`, `unlock_time`.
    - `Job.model_fields["blockchain_identifier"].alias == "blockchainIdentifier"`.
  </done>
</task>

## Must-Haves

- [ ] `JobStatus.AWAITING_INPUT = "awaiting_input"` — 5th member
- [ ] `RUNNING → AWAITING_INPUT` legal; `AWAITING_INPUT → RUNNING` legal; all terminal states unchanged
- [ ] `Job`: 4 new `int`/`str` fields with correct camelCase `Field(alias=...)`
- [ ] `populate_by_name=True` in `model_config`
- [ ] `blockchain_identifier` gets alias `blockchainIdentifier`

## Success Criteria

- [ ] `from app.domain.models import JobStatus; assert len(JobStatus) == 5`
- [ ] `validate_transition(JobStatus.RUNNING, JobStatus.AWAITING_INPUT)` → no raise
- [ ] `validate_transition(JobStatus.AWAITING_INPUT, JobStatus.RUNNING)` → no raise
- [ ] `validate_transition(JobStatus.AWAITING_INPUT, JobStatus.COMPLETED)` → raises `InvalidStateTransitionError`
