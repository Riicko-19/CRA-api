from typing import Optional

from app.domain.models import Job, JobStatus
from app.repository.job_repo import InMemoryJobRepository


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
