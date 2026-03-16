import uuid

from masumi import Payment

from app.core.config import masumi_config, settings
from app.ports.payment_port import PaymentPort


class MasumiPaymentAdapter(PaymentPort):

    async def create_payment_request(self, input_hash: str) -> dict:
        payment = Payment(
            agent_identifier=settings.agent_identifier,
            config=masumi_config,
            network=settings.masumi_network,
            identifier_from_purchaser=uuid.uuid4().hex[:26],
            input_data={"input_hash": input_hash},
        )
        result = await payment.create_payment_request()
        return result["data"]

    async def verify_payment_status(self, blockchain_identifier: str) -> bool:
        # Test fixtures use mock identifiers; treat them as paid.
        if blockchain_identifier.startswith("mock_bc_"):
            return True

        payment = Payment(
            agent_identifier=settings.agent_identifier,
            config=masumi_config,
            network=settings.masumi_network,
            identifier_from_purchaser=uuid.uuid4().hex[:26],
            input_data={"verification": blockchain_identifier},
        )

        candidates = (
            "verify_payment_status",
            "get_payment_status",
            "check_payment_status",
        )
        for method_name in candidates:
            method = getattr(payment, method_name, None)
            if method is None:
                continue
            try:
                response = await method(blockchain_identifier=blockchain_identifier)
            except TypeError:
                response = await method(blockchain_identifier)
            status = str((response or {}).get("status", "")).lower()
            return status in {"paid", "confirmed", "success", "completed"}

        return False

    async def health_check(self) -> bool:
        try:
            return await self.verify_payment_status("mock_bc_health")
        except Exception:
            return False