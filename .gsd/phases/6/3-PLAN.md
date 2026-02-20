---
phase: 6
plan: 3
wave: 3
gap_closure: false
---

# Plan 6.3: Mock Payment SDK in Test Suite

## Objective

Patch `Payment.create_payment_request` in Pytest so tests never hit a live Cardano node. All 50 existing TCs must continue to pass; no new tests must fail.

## Context

- `tests/test_phase3_endpoints.py` — has `client` fixture + tests that call `/start_job`
- `tests/test_phase4_full_flow.py` — has `client` fixture + tests that call `/start_job`
- `tests/test_phase5_mip003.py` — calls `_create_job` helper which hits `/start_job`
- `tests/test_phase1_models.py`, `tests/test_phase2_repository.py` — **no HTTP calls**, but `repo.create()` signature changed → tests that call `repo.create()` directly must be updated to pass all 6 args

## Dummy Payload

```python
MOCK_PAYMENT_DATA = {
    "data": {
        "blockchainIdentifier": "mock_bc_abcd1234",
        "sellerVKey":           "mock_vkey_abcd1234",
        "payByTime":            9_999_999_999,
        "submitResultTime":     9_999_999_999 + 3600,
        "unlockTime":           9_999_999_999 + 86400,
    }
}
```

## Tasks

<task type="auto">
  <name>Add autouse mock fixture to conftest.py</name>
  <files>tests/conftest.py</files>
  <action>
    Create (or update) `tests/conftest.py` with an `autouse=True` fixture that patches
    `Payment.create_payment_request` for ALL test files:

    ```python
    import pytest
    from unittest.mock import AsyncMock, patch

    MOCK_PAYMENT_DATA = {
        "data": {
            "blockchainIdentifier": "mock_bc_abcd1234",
            "sellerVKey":           "mock_vkey_abcd1234",
            "payByTime":            9_999_999_999,
            "submitResultTime":     9_999_999_999 + 3600,
            "unlockTime":           9_999_999_999 + 86400,
        }
    }

    @pytest.fixture(autouse=True)
    def mock_payment_sdk():
        """Patch masumi.Payment.create_payment_request for all tests."""
        with patch(
            "masumi.Payment.create_payment_request",
            new_callable=AsyncMock,
            return_value=MOCK_PAYMENT_DATA,
        ) as mock:
            yield mock
    ```

    Using `autouse=True` means we don't need to manually add the patch to every
    test file — it just works globally.
  </action>
</task>

<task type="auto">
  <name>Update test_phase2_repository.py — repo.create() calls</name>
  <files>tests/test_phase2_repository.py</files>
  <action>
    `repo.create()` now requires 6 keyword args. Update every direct call:

    BEFORE:
    ```python
    job = repo.create(input_hash="a" * 64)
    ```

    AFTER:
    ```python
    job = repo.create(
        input_hash="a" * 64,
        blockchain_identifier="mock_bc_test",
        pay_by_time=9_999_999_999,
        seller_vkey="mock_vkey_test",
        submit_result_time=9_999_999_999 + 3600,
        unlock_time=9_999_999_999 + 86400,
    )
    ```

    All calls in: `test_create_job_initial_state`, `test_get_returns_created_job`,
    `test_legal_transition_updates_job`, `test_illegal_transition_raises`,
    `test_count_reflects_stored_jobs`, `test_concurrent_creates_are_unique`,
    `test_completed_job_stores_result` (worker lambda too).
  </action>
</task>

## Must-Haves

- [ ] `tests/conftest.py` patches `masumi.Payment.create_payment_request` globally with `autouse=True`
- [ ] All `repo.create()` direct calls in `test_phase2_repository.py` pass 6 args
- [ ] No test file imports or patches anything masumi-specific themselves (conftest handles it)
- [ ] 50 existing TCs still pass (count may increase if conftest adds parametrize)

## Success Criteria

- [ ] `pytest tests/ -v --tb=short` → zero failures
- [ ] Running with `PAYMENT_API_KEY=live_key pytest tests/` still uses the mock (autouse isolates tests from real network)
