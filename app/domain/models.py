from __future__ import annotations

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
    pay_by_time: int        = Field(alias="payByTime")
    seller_vkey: str        = Field(alias="sellerVKey")
    submit_result_time: int = Field(alias="submitResultTime")
    unlock_time: int        = Field(alias="unlockTime")


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
