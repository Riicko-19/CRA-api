from abc import ABC, abstractmethod


class NormalisationPort(ABC):

    @abstractmethod
    async def normalise(self, raw_input: dict) -> dict: ...

    @abstractmethod
    async def health_check(self) -> bool: ...