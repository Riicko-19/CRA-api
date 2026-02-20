---
phase: 6
description: Masumi SDK Integration — real on-chain payment request (replacing mock timestamps)
plans: 3
---

# Phase 6: Masumi SDK Integration

## Summary

Replace the mocked `pay_by_time`/`seller_vkey`/`submit_result_time`/`unlock_time` generate logic in `job_repo.py` with real calls to the masumi Python SDK's `Payment.create_payment_request()`.

| Plan | Focus | Files |
|------|-------|-------|
| 6.1 | Dependencies + config module | `requirements.txt`, `app/core/__init__.py`, `app/core/config.py` |
| 6.2 | Async service layer → real SDK call | `app/services/job_service.py`, `app/repository/job_repo.py`, `app/routers/jobs.py` |
| 6.3 | Mock SDK in tests via conftest.py | `tests/conftest.py`, `tests/test_phase2_repository.py` |

## Plan Index

- [6.1-PLAN.md](.gsd/phases/6/1-PLAN.md) — Dependencies & Config
- [6.2-PLAN.md](.gsd/phases/6/2-PLAN.md) — Async Service Layer
- [6.3-PLAN.md](.gsd/phases/6/3-PLAN.md) — Test Suite Mocking

## Key Design Decisions

### 1. SDK Import Path
```python
from masumi import Config, Payment
```
`Config(payment_service_url=..., payment_api_key=...)`  
`Payment(agent_identifier=..., config=..., network=..., identifier_from_purchaser=..., input_data=...)`

### 2. Response Field Mapping
```
result["data"]["blockchainIdentifier"] → Job.blockchain_identifier
result["data"]["sellerVKey"]           → Job.seller_vkey
result["data"]["payByTime"]            → Job.pay_by_time
result["data"]["submitResultTime"]     → Job.submit_result_time
result["data"]["unlockTime"]           → Job.unlock_time
```

### 3. create_job becomes async
`create_job` must be `async def` and the `/start_job` route must be `async def` + `await`.  
`advance_job_state` stays synchronous — no change needed.

### 4. repo.create() signature change
`repo.create()` drops its internal timestamp generation and accepts the 5 blockchain values as explicit keyword args. Direct callers in `test_phase2_repository.py` must be updated.

### 5. Test isolation via autouse fixture
`conftest.py` patches `masumi.Payment.create_payment_request` globally with `autouse=True` + `AsyncMock`. Tests never hit a live Cardano node.

## Dependency Order

```
Plan 6.1 (deps+config) → Plan 6.2 (service+router) → Plan 6.3 (tests)
```

## Final Gate

```
pytest tests/ -v --tb=short
```

Expected: ≥ 50 passed, 0 failed.
