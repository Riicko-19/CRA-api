from __future__ import annotations

from pydantic_settings import BaseSettings
from masumi import Config as MasumiConfig


class Settings(BaseSettings):
    agent_identifier: str = "mock_agent_id"
    seller_vkey: str = "mock_seller_vkey"
    payment_service_url: str = "https://payment.masumi.network/api/v1"
    payment_api_key: str = "mock_api_key"
    masumi_network: str = "Preprod"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

masumi_config = MasumiConfig(
    payment_service_url=settings.payment_service_url,
    payment_api_key=settings.payment_api_key,
)
