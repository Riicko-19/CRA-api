---
phase: 7
status: planning
---

# Phase 7: Qdrant DB Integration

## Objective

Integrate the asynchronous Qdrant client and wire up global exception handlers to catch database connection drops, returning a clean `503` instead of a `500` crash. Keep the test suite entirely isolated from the network.

## Plans

| # | File | Title | Key outputs |
|---|------|--------|-------------|
| [7.1](1-PLAN.md) | `requirements.txt`, `app/core/config.py` | Dependencies & Config | `qdrant-client` dep; `qdrant_url`, `qdrant_api_key` settings |
| [7.2](2-PLAN.md) | `app/db/__init__.py`, `app/db/qdrant.py` | Async Qdrant Client | `AsyncQdrantClient` singleton, `get_qdrant()` dependency |
| [7.3](3-PLAN.md) | `app/main.py` | Failure-Proof Exception Handlers | 503 handlers for `ResponseHandlingException` + `UnexpectedResponse` |
| [7.4](4-PLAN.md) | `tests/conftest.py` | Test Isolation | `autouse=True` patch for `qdrant_client.AsyncQdrantClient` |

## Key Design Decisions

### Import path for exceptions
`qdrant_client.http.exceptions` — NOT `qdrant_client.exceptions`.  
Both `ResponseHandlingException` and `UnexpectedResponse` live in the HTTP sub-package.

### `:memory:` default
`settings.qdrant_url = ":memory:"` means no network socket is ever opened during local dev or tests. The `AsyncQdrantClient` detects this special value and stays in-process.

### get_qdrant() pattern
A plain `def get_qdrant() -> AsyncQdrantClient` (not `async def` generator) is correct here because the singleton is initialised at import time — no per-request setup/teardown needed.

### 503 response body — exact string
```json
{"detail": "Vector database temporarily unavailable. Please try again later."}
```
Both Qdrant handlers return this **identical** body. Tests asserting the 503 shape must use this exact string.

### Conftest patch order
`mock_payment_sdk` (masumi) and `mock_qdrant_client` (Qdrant) are independent `autouse=True` fixtures — both run for every test, in declaration order. No conflicts.

## Dependency Order

```
7.1 → 7.2 → 7.3 → 7.4
```
- 7.2 depends on 7.1 (`settings.qdrant_url` must exist)
- 7.3 depends on 7.1 (`qdrant-client` must be installed for import)
- 7.4 depends on 7.2 (`app/db/qdrant.py` must exist for the mock target to resolve)

## Final Gate Criteria

- [ ] `pip show qdrant-client` → version ≥ 1.9.0
- [ ] `python -c "from app.db.qdrant import get_qdrant; print(type(get_qdrant()))"` → `AsyncQdrantClient`
- [ ] `python -c "from app.main import create_app; app = create_app(); print(len(app.exception_handlers))"` → `6`
- [ ] `pytest tests/ -v` → **50/50 passed** in < 5 s (no live network)
