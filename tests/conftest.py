import pytest
from unittest.mock import AsyncMock, patch

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
