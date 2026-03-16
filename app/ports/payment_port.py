from abc import ABC, abstractmethod


class PaymentPort(ABC):

    @abstractmethod
    async def create_payment_request(self, input_hash: str) -> dict: ...

    @abstractmethod
    async def verify_payment_status(self, blockchain_identifier: str) -> bool: ...

    @abstractmethod
    async def health_check(self) -> bool: ...