import pytest

from app.adapters.llm_normalisation_adapter import LLMNormalisationAdapter
from app.adapters.orchestrator_adapter import OrchestratorAdapter
from app.core.config import settings
from app.domain.models import JobStatus
from app.repository.job_repo import InMemoryJobRepository
from app.services.agent_runner import execute_agent_task


@pytest.mark.asyncio
async def test_llm_normaliser_fallback_without_api_key(monkeypatch):
    adapter = LLMNormalisationAdapter()
    monkeypatch.setattr(settings, "openrouter_api_key", "")
    raw = {
        "target_domain": "https://example.com",
        "my_product_usp": "USP",
        "ideal_customer_profile": "ICP",
    }
    normalised = await adapter.normalise(raw)
    assert normalised == raw


@pytest.mark.asyncio
async def test_orchestrator_mock_url_returns_result(monkeypatch):
    adapter = OrchestratorAdapter()
    monkeypatch.setattr(settings, "orchestrator_url", "mock://orchestrator")
    result = await adapter.execute("job-123", {"k": "v"})
    assert "job-123" in result


class _NormaliserOk:
    async def normalise(self, raw_input: dict) -> dict:
        return {"normalised": raw_input}


class _OrchestratorOk:
    async def execute(self, job_id: str, normalised_input: dict) -> str:
        return f"done:{job_id}:{normalised_input['normalised'].get('x')}"


class _OrchestratorFails:
    async def execute(self, job_id: str, normalised_input: dict) -> str:
        raise RuntimeError("orchestrator down")


@pytest.mark.asyncio
async def test_agent_runner_completes_job():
    repo = InMemoryJobRepository()
    job = repo.create(
        input_hash="a" * 64,
        blockchain_identifier="mock_bc_test",
        pay_by_time=9_999_999_999,
        seller_vkey="mock_vkey_test",
        submit_result_time=9_999_999_999 + 3600,
        unlock_time=9_999_999_999 + 86_400,
    )
    repo.update_status(job.job_id, JobStatus.RUNNING)

    await execute_agent_task(
        job.job_id,
        repo,
        _NormaliserOk(),
        _OrchestratorOk(),
        {"x": "y"},
    )
    completed = repo.get(job.job_id)
    assert completed.status == JobStatus.COMPLETED
    assert completed.result is not None


@pytest.mark.asyncio
async def test_agent_runner_marks_failed_on_exception():
    repo = InMemoryJobRepository()
    job = repo.create(
        input_hash="b" * 64,
        blockchain_identifier="mock_bc_test",
        pay_by_time=9_999_999_999,
        seller_vkey="mock_vkey_test",
        submit_result_time=9_999_999_999 + 3600,
        unlock_time=9_999_999_999 + 86_400,
    )
    repo.update_status(job.job_id, JobStatus.RUNNING)

    await execute_agent_task(
        job.job_id,
        repo,
        _NormaliserOk(),
        _OrchestratorFails(),
        {"x": "y"},
    )
    failed = repo.get(job.job_id)
    assert failed.status == JobStatus.FAILED
    assert "orchestrator down" in (failed.error or "")
