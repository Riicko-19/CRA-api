from abc import ABC, abstractmethod


class PaymentPort(ABC):

    @abstractmethod
    async def create_payment_request(self, input_hash: str) -> dict: ...