from __future__ import annotations

import uuid
from typing import Optional

from masumi import Payment

from app.core.config import settings, masumi_config
from app.domain.models import Job, JobStatus
from app.repository.job_repo import InMemoryJobRepository


async def create_job(repo: InMemoryJobRepository, input_hash: str) -> Job:
    """Call the masumi Payment SDK to register a real on-chain payment request."""
    payment = Payment(
        agent_identifier=settings.agent_identifier,
        config=masumi_config,
        network=settings.masumi_network,
        identifier_from_purchaser=uuid.uuid4().hex[:26],  # 26-char buyer hex placeholder
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
