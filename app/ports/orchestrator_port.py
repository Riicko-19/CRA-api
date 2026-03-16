from abc import ABC, abstractmethod


class OrchestratorPort(ABC):

    @abstractmethod
    async def execute(self, job_id: str, normalised_input: dict) -> str: ...