import pytest
from datetime import datetime
from pydantic import ValidationError

from app.domain.models import Job, JobStatus, validate_transition
from app.domain.exceptions import InvalidStateTransitionError


# --- Helpers ---

def _make_valid_job(**overrides) -> Job:
    """Factory for a valid Job instance."""
    defaults = dict(
        job_id="test-job-id-0001",
        status=JobStatus.AWAITING_PAYMENT,
        input_hash="a" * 64,
        blockchain_identifier="mock_bc_test",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    defaults.update(overrides)
    return Job(**defaults)


# TC-1.1: JobStatus has exactly 4 members
def test_job_status_members():
    assert set(JobStatus) == {
        JobStatus.AWAITING_PAYMENT,
        JobStatus.RUNNING,
        JobStatus.COMPLETED,
        JobStatus.FAILED,
    }


# TC-1.2: Job model rejects extra fields
def test_job_rejects_extra_fields():
    with pytest.raises(ValidationError):
        Job(
            job_id="abc",
            status=JobStatus.AWAITING_PAYMENT,
            input_hash="x" * 64,
            blockchain_identifier="mock_bc_abc",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            EXTRA_FIELD="should_fail",
        )


# TC-1.3: Job model is frozen (immutable)
def test_job_is_frozen():
    job = _make_valid_job()
    with pytest.raises(ValidationError):
        job.status = JobStatus.RUNNING


# TC-1.4: Legal transitions do not raise
@pytest.mark.parametrize("from_s,to_s", [
    (JobStatus.AWAITING_PAYMENT, JobStatus.RUNNING),
    (JobStatus.RUNNING, JobStatus.COMPLETED),
    (JobStatus.RUNNING, JobStatus.FAILED),
])
def test_legal_transitions(from_s, to_s):
    validate_transition(from_s, to_s)  # must NOT raise


# TC-1.5: Illegal transitions raise InvalidStateTransitionError
@pytest.mark.parametrize("from_s,to_s", [
    (JobStatus.AWAITING_PAYMENT, JobStatus.COMPLETED),
    (JobStatus.AWAITING_PAYMENT, JobStatus.FAILED),
    (JobStatus.COMPLETED, JobStatus.RUNNING),
    (JobStatus.FAILED, JobStatus.RUNNING),
    (JobStatus.COMPLETED, JobStatus.AWAITING_PAYMENT),
    (JobStatus.RUNNING, JobStatus.AWAITING_PAYMENT),
])
def test_illegal_transitions(from_s, to_s):
    with pytest.raises(InvalidStateTransitionError):
        validate_transition(from_s, to_s)


# TC-1.6: InvalidStateTransitionError carries state info
def test_invalid_transition_error_attributes():
    try:
        validate_transition(JobStatus.COMPLETED, JobStatus.RUNNING)
        pytest.fail("Expected InvalidStateTransitionError")
    except InvalidStateTransitionError as e:
        assert e.from_state == "completed"
        assert e.to_state == "running"
