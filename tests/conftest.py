import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.config import limiter

# Dummy payload matching the masumi SDK response shape.
# payByTime = year 2286 — always passes test_pay_by_time_is_future.
MOCK_PAYMENT_DATA = {
    "data": {
        "blockchainIdentifier": "mock_bc_abcd1234",
        "sellerVKey":           "mock_vkey_abcd1234",
        "payByTime":            9_999_999_999,
        "submitResultTime":     9_999_999_999 + 3_600,
        "unlockTime":           9_999_999_999 + 86_400,
    }
}


@pytest.fixture(autouse=True)
def mock_payment_sdk():
    """Patch masumi.Payment.create_payment_request for ALL tests.

    autouse=True means every test — in every file — gets this patch
    automatically. Tests never hit a live Cardano node.
    """
    with patch(
        "masumi.Payment.create_payment_request",
        new_callable=AsyncMock,
        return_value=MOCK_PAYMENT_DATA,
    ) as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_qdrant_client():
    """Patch qdrant_client.AsyncQdrantClient for ALL tests.

    autouse=True means every test — in every file — gets this patch
    automatically. Tests never attempt a live TCP connection to Qdrant.
    """
    with patch(
        "qdrant_client.AsyncQdrantClient",
        return_value=MagicMock(),
    ) as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_agent_sleep():
    """Patch asyncio.sleep inside agent_runner for ALL tests.

    Prevents any real 5-second pause when execute_agent_task is invoked
    directly inside a test.
    """
    with patch(
        "app.services.agent_runner.asyncio.sleep",
        new_callable=AsyncMock,
    ) as mock:
        yield mock


@pytest.fixture(autouse=True)
def reset_limiter():
    """Reset the slowapi Limiter's in-memory storage before each test.

    The limiter singleton (from app.core.config) persists request counters
    across tests. Without this reset, tests that call /start_job will
    exhaust the 5/minute limit and cause subsequent tests to get 429s
    unexpectedly. Resetting between tests makes each test independent.
    """
    limiter._storage.reset()
    yield
