import threading
import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.core.config import settings
from app.domain.exceptions import JobNotFoundError
from app.domain.models import Job, JobStatus, validate_transition
from app.ports.job_repository_port import JobRepositoryPort


logger = logging.getLogger(__name__)


class QdrantJobRepository(JobRepositoryPort):
    def __init__(self, collection_name: str = "jobs"):
        self._lock = threading.RLock()
        self._collection_name = collection_name
        if settings.qdrant_url == ":memory:":
            self._client = QdrantClient(":memory:")
        else:
            self._client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        if self._client.collection_exists(self._collection_name):
            return
        self._client.create_collection(
            collection_name=self._collection_name,
            vectors_config=VectorParams(size=1, distance=Distance.COSINE),
        )

    @staticmethod
    def _to_payload(job: Job) -> dict:
        payload = job.model_dump(by_alias=True)
        payload["status"] = job.status.value
        payload["created_at"] = job.created_at.isoformat()
        payload["updated_at"] = job.updated_at.isoformat()
        return payload

    @staticmethod
    def _from_payload(payload: dict) -> Job:
        normalized = dict(payload)
        normalized["created_at"] = datetime.fromisoformat(normalized["created_at"])
        normalized["updated_at"] = datetime.fromisoformat(normalized["updated_at"])
        normalized["status"] = JobStatus(normalized["status"])
        return Job(**normalized)

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
            self._client.upsert(
                collection_name=self._collection_name,
                points=[PointStruct(id=job_id, vector=[0.0], payload=self._to_payload(job))],
            )
        return job

    def get(self, job_id: str) -> Job:
        with self._lock:
            points = self._client.retrieve(
                collection_name=self._collection_name,
                ids=[job_id],
                with_payload=True,
            )
        if not points:
            raise JobNotFoundError(job_id)
        return self._from_payload(points[0].payload or {})

    def update_status(
        self,
        job_id: str,
        target: JobStatus,
        result: Optional[str] = None,
        error: Optional[str] = None,
    ) -> Job:
        with self._lock:
            current = self.get(job_id)
            validate_transition(current.status, target)
            previous = current.status
            updated = current.model_copy(update={
                "status": target,
                "updated_at": datetime.now(timezone.utc),
                "result": result,
                "error": error,
            })
            self._client.upsert(
                collection_name=self._collection_name,
                points=[PointStruct(id=job_id, vector=[0.0], payload=self._to_payload(updated))],
            )
        logger.info(
            "Job state transition",
            extra={
                "job_id": job_id,
                "from_state": previous.value,
                "to_state": target.value,
            },
        )
        return updated

    def count(self) -> int:
        with self._lock:
            response = self._client.count(collection_name=self._collection_name, exact=True)
        return int(response.count)

    def recover_stale_running_jobs(self, timeout_minutes: int) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)
        recovered = 0
        with self._lock:
            points, _ = self._client.scroll(
                collection_name=self._collection_name,
                with_payload=True,
                limit=10_000,
            )
            for point in points:
                payload = point.payload or {}
                if payload.get("status") != JobStatus.RUNNING.value:
                    continue
                updated_at = datetime.fromisoformat(str(payload["updated_at"]))
                if updated_at > cutoff:
                    continue
                payload["status"] = JobStatus.FAILED.value
                payload["error"] = "Job timed out — recovered on restart"
                payload["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._client.upsert(
                    collection_name=self._collection_name,
                    points=[PointStruct(id=point.id, vector=[0.0], payload=payload)],
                )
                recovered += 1
        return recovered

    def health_check(self) -> bool:
        try:
            self._client.count(collection_name=self._collection_name, exact=False)
            return True
        except Exception:
            return False