---
phase: 5
description: MIP-003 Compliance Refactor (AWAITING_INPUT, Job fields, /availability update, test suite)
plans: 3
---

# Phase 5: MIP-003 Compliance Refactor

## Summary

Full MIP-003 compliance refactor across 3 sequential plans:

| Plan | Focus | Files |
|------|-------|-------|
| 5.1 | Domain model — `AWAITING_INPUT` + 4 new `Job` fields + camelCase aliases | `app/domain/models.py` |
| 5.2 | Availability response + repository mock timestamps | `app/routers/jobs.py`, `app/repository/job_repo.py` |
| 5.3 | Update all 4 test suites + write `test_phase5_mip003.py` (8 TCs) | `tests/*.py` |

## Plan Index

- [5.1-PLAN.md](.gsd/phases/5/1-PLAN.md) — Domain models
- [5.2-PLAN.md](.gsd/phases/5/2-PLAN.md) — Availability endpoint & repository
- [5.3-PLAN.md](.gsd/phases/5/3-PLAN.md) — Test suite updates & gate

## Key Design Decisions

### 1. camelCase aliases via `Field(alias=...)`
All MIP-003 fields use Pydantic `Field(alias="camelCase")` with `populate_by_name=True` in `model_config`.  
Routes returning `Job` must add `response_model=Job, response_model_by_alias=True` to serialise aliases in HTTP responses.

### 2. AWAITING_INPUT state position
```
AWAITING_PAYMENT → RUNNING ⇆ AWAITING_INPUT
                ↓
            COMPLETED / FAILED
```
`AWAITING_INPUT → COMPLETED/FAILED` is **illegal** — must return to `RUNNING` first.

### 3. /availability response (MIP-003)
```json
{"status": "available", "service_type": "masumi-agent"}
```
`queue_depth` removed entirely. TC-3.8 is updated to assert unique job IDs instead.

### 4. Mock timestamp offsets
| Field | Offset | Value |
|-------|--------|-------|
| `pay_by_time` | +1h | `now_ts + 3600` |
| `submit_result_time` | +2h | `now_ts + 7200` |
| `unlock_time` | +24h | `now_ts + 86400` |
| `seller_vkey` | prefix | `"mock_vkey_" + job_id[:8]` |

## Dependency Order

```
Plan 5.1 (models) → Plan 5.2 (repo+router) → Plan 5.3 (tests)
```

Each plan is a wave gate — must fully pass before the next executes.

## Final Gate

```
pytest tests/ -v --tb=short
```

Expected: All tests pass (count ≥ 37, increased by new parametrize entries and 8+ new TCs in test_phase5_mip003.py).
