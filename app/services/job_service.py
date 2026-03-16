from __future__ import annotations

from typing import Optional

from app.domain.models import Job, JobStatus
from app.ports.job_repository_port import JobRepositoryPort
from app.ports.payment_port import PaymentPort


async def create_job(
    repo: JobRepositoryPort,
    payment_port: PaymentPort,
    input_hash: str,
) -> Job:
    data = await payment_port.create_payment_request(input_hash)
    return repo.create(
        input_hash=input_hash,
        blockchain_identifier=data["blockchainIdentifier"],
        pay_by_time=int(data["payByTime"]),
        seller_vkey=data["sellerVKey"],
        submit_result_time=int(data["submitResultTime"]),
        unlock_time=int(data["unlockTime"]),
    )


def advance_job_state(
    repo: JobRepositoryPort,
    job_id: str,
    target: JobStatus,
    result: Optional[str] = None,
    error: Optional[str] = None,
) -> Job:
    return repo.update_status(job_id, target, result=result, error=error)