from __future__ import annotations

import asyncio

from app.domain.models import JobStatus
from app.ports.job_repository_port import JobRepositoryPort
from app.ports.normalisation_port import NormalisationPort
from app.ports.orchestrator_port import OrchestratorPort
from app.services import job_service


async def execute_agent_task(
  job_id: str,
  repo: JobRepositoryPort,
  normaliser: NormalisationPort,
  orchestrator: OrchestratorPort,
  raw_input: dict,
) -> None:
  await asyncio.sleep(5)
  try:
    normalised = await normaliser.normalise(raw_input)
    result = await orchestrator.execute(job_id, normalised)
    job_service.advance_job_state(
      repo,
      job_id,
      JobStatus.COMPLETED,
      result=result,
    )
  except Exception as exc:
    job_service.advance_job_state(
      repo,
      job_id,
      JobStatus.FAILED,
      error=str(exc),
    )
