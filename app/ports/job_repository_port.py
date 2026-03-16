from abc import ABC, abstractmethod
from typing import Optional
from app.domain.models import Job, JobStatus


class JobRepositoryPort(ABC):

    @abstractmethod
    def create(
        self,
        input_hash: str,
        blockchain_identifier: str,
        pay_by_time: int,
        seller_vkey: str,
        submit_result_time: int,
        unlock_time: int,
    ) -> Job: ...

    @abstractmethod
    def get(self, job_id: str) -> Job: ...

    @abstractmethod
    def update_status(
        self,
        job_id: str,
        target: JobStatus,
        result: Optional[str] = None,
        error: Optional[str] = None,
    ) -> Job: ...

    @abstractmethod
    def count(self) -> int: ...