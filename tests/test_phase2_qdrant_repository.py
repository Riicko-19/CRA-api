from datetime import datetime, timedelta, timezone
import uuid

from qdrant_client.models import PointStruct

from app.domain.models import JobStatus
from app.repository.qdrant_job_repo import QdrantJobRepository


def _make_repo() -> QdrantJobRepository:
    return QdrantJobRepository(collection_name=f"jobs_test_phase2_{uuid.uuid4().hex}")


def test_qdrant_repository_create_get_update_count():
    repo = _make_repo()
    assert repo.count() == 0

    job = repo.create(
        input_hash="x" * 64,
        blockchain_identifier="mock_bc_qdrant",
        pay_by_time=9_999_999_999,
        seller_vkey="mock_vkey_qdrant",
        submit_result_time=9_999_999_999 + 3600,
        unlock_time=9_999_999_999 + 86_400,
    )
    assert repo.count() == 1

    fetched = repo.get(job.job_id)
    assert fetched.job_id == job.job_id
    assert fetched.status == JobStatus.AWAITING_PAYMENT

    running = repo.update_status(job.job_id, JobStatus.RUNNING)
    assert running.status == JobStatus.RUNNING


def test_qdrant_recover_stale_running_jobs():
    repo = _make_repo()
    job = repo.create(
        input_hash="y" * 64,
        blockchain_identifier="mock_bc_qdrant_2",
        pay_by_time=9_999_999_999,
        seller_vkey="mock_vkey_qdrant_2",
        submit_result_time=9_999_999_999 + 3600,
        unlock_time=9_999_999_999 + 86_400,
    )
    repo.update_status(job.job_id, JobStatus.RUNNING)

    stale_payload = repo.get(job.job_id).model_dump(by_alias=True)
    stale_payload["status"] = JobStatus.RUNNING.value
    stale_payload["updated_at"] = (datetime.now(timezone.utc) - timedelta(minutes=61)).isoformat()
    stale_payload["created_at"] = stale_payload["created_at"].isoformat()
    repo._client.upsert(
        collection_name=repo._collection_name,
        points=[PointStruct(id=job.job_id, vector=[0.0], payload=stale_payload)],
    )

    recovered = repo.recover_stale_running_jobs(timeout_minutes=30)
    assert recovered >= 1

    failed = repo.get(job.job_id)
    assert failed.status == JobStatus.FAILED
    assert failed.error == "Job timed out — recovered on restart"
