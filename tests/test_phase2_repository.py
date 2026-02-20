import threading
import pytest

from app.domain.models import JobStatus
from app.domain.exceptions import JobNotFoundError, InvalidStateTransitionError
from app.repository.job_repo import InMemoryJobRepository


# TC-2.1: create() returns a job in AWAITING_PAYMENT state
def test_create_job_initial_state():
    repo = InMemoryJobRepository()
    job = repo.create(input_hash="a" * 64)
    assert job.status == JobStatus.AWAITING_PAYMENT
    assert job.input_hash == "a" * 64
    assert job.blockchain_identifier.startswith("mock_bc_")
    assert job.result is None
    assert job.error is None


# TC-2.2: get() returns the same job that was created
def test_get_returns_created_job():
    repo = InMemoryJobRepository()
    job = repo.create(input_hash="b" * 64)
    retrieved = repo.get(job.job_id)
    assert retrieved.job_id == job.job_id


# TC-2.3: get() raises JobNotFoundError for unknown ID
def test_get_unknown_job_raises():
    repo = InMemoryJobRepository()
    with pytest.raises(JobNotFoundError):
        repo.get("nonexistent-id")


# TC-2.4: Legal state transition updates status and updated_at
def test_legal_transition_updates_job():
    repo = InMemoryJobRepository()
    job = repo.create(input_hash="c" * 64)
    updated = repo.update_status(job.job_id, JobStatus.RUNNING)
    assert updated.status == JobStatus.RUNNING
    assert updated.updated_at >= job.updated_at


# TC-2.5: Illegal state transition raises InvalidStateTransitionError
def test_illegal_transition_raises():
    repo = InMemoryJobRepository()
    job = repo.create(input_hash="d" * 64)
    with pytest.raises(InvalidStateTransitionError):
        repo.update_status(job.job_id, JobStatus.COMPLETED)  # skip RUNNING


# TC-2.6: count() reflects stored jobs
def test_count_reflects_stored_jobs():
    repo = InMemoryJobRepository()
    assert repo.count() == 0
    repo.create("e" * 64)
    repo.create("f" * 64)
    assert repo.count() == 2


# TC-2.7: Thread-safety — concurrent creates produce unique IDs
def test_concurrent_creates_are_unique():
    repo = InMemoryJobRepository()
    ids = []
    lock = threading.Lock()

    def worker():
        job = repo.create("g" * 64)
        with lock:
            ids.append(job.job_id)

    threads = [threading.Thread(target=worker) for _ in range(100)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(ids) == 100
    assert len(set(ids)) == 100  # all unique


# TC-2.8: completed job with result is stored correctly
def test_completed_job_stores_result():
    repo = InMemoryJobRepository()
    job = repo.create("h" * 64)
    repo.update_status(job.job_id, JobStatus.RUNNING)
    done = repo.update_status(
        job.job_id, JobStatus.COMPLETED, result="output_data"
    )
    assert done.status == JobStatus.COMPLETED
    assert done.result == "output_data"
    assert done.error is None
