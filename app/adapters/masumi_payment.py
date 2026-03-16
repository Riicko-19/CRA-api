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