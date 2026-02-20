import threading
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.domain.models import Job, JobStatus, validate_transition
from app.domain.exceptions import JobNotFoundError


class InMemoryJobRepository:
    def __init__(self):
        self._store: dict[str, Job] = {}
        self._lock = threading.Lock()

    def create(
        self,
        input_hash: str,
        blockchain_identifier: str,
        pay_by_time: int,
        seller_vkey: str,
        submit_result_time: int,
        unlock_time: int,
    ) -> Job:
        job_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        job = Job(
            job_id=job_id,
            status=JobStatus.AWAITING_PAYMENT,
            input_hash=input_hash,
            blockchain_identifier=blockchain_identifier,
            created_at=now,
            updated_at=now,
            pay_by_time=pay_by_time,
            seller_vkey=seller_vkey,
            submit_result_time=submit_result_time,
            unlock_time=unlock_time,
        )
        with self._lock:
            self._store[job_id] = job
        return job

    def get(self, job_id: str) -> Job:
        with self._lock:
            job = self._store.get(job_id)
        if job is None:
            raise JobNotFoundError(job_id)
        return job

    def update_status(
        self,
        job_id: str,
        target: JobStatus,
        result: Optional[str] = None,
        error: Optional[str] = None,
    ) -> Job:
        with self._lock:
            job = self._store.get(job_id)
            if job is None:
                raise JobNotFoundError(job_id)
            validate_transition(job.status, target)
            updated = job.model_copy(update={
                "status": target,
                "updated_at": datetime.now(timezone.utc),
                "result": result,
                "error": error,
            })
            self._store[job_id] = updated
        return updated

    def count(self) -> int:
        with self._lock:
            return len(self._store)
