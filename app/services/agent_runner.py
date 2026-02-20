from __future__ import annotations

import asyncio

from app.domain.models import JobStatus
from app.repository.job_repo import InMemoryJobRepository
from app.services import job_service


async def execute_agent_task(job_id: str, repo: InMemoryJobRepository) -> None:
    """Background task — simulates LLM/Qdrant work then marks the job COMPLETED.

    Called via BackgroundTasks.add_task(); the HTTP response is already sent
    before this coroutine runs, preventing any worker starvation.

    The function is called from two code paths:
      - /start_job   → job is in AWAITING_PAYMENT; we skip two transitions here
                       (payment is mocked / bypassed in Phase 8 flow)
      - /provide_input → job is already RUNNING (router advanced it first)

    To handle both paths safely, we check current status and only advance
    through the states that still need advancing.

    Steps:
      1. await 5 s  — placeholder for real async LLM/Qdrant calls
      2. If AWAITING_PAYMENT → advance to RUNNING first
      3. Advance RUNNING → COMPLETED
    """
    await asyncio.sleep(5)

    current = repo.get(job_id)
    if current.status == JobStatus.AWAITING_PAYMENT:
        job_service.advance_job_state(repo, job_id, JobStatus.RUNNING)

    job_service.advance_job_state(
        repo,
        job_id,
        JobStatus.COMPLETED,
        result="Task executed successfully",
    )
