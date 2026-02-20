---
phase: 7
plan: 4
wave: 4
gap_closure: false
---

# Plan 7.4: Test Isolation — Mock AsyncQdrantClient

## Objective

Add a second `autouse=True` fixture to `tests/conftest.py` that patches `qdrant_client.AsyncQdrantClient` globally, ensuring the existing 50-test suite (and all future tests) never attempt a live Qdrant connection.

## Context

- `tests/conftest.py` — currently has one `autouse=True` fixture (`mock_payment_sdk`)
- `app/db/qdrant.py` creates `_client = AsyncQdrantClient(...)` at module import time
- The patch target must be `"qdrant_client.AsyncQdrantClient"` (public import path)
- `MagicMock` (not `AsyncMock`) is appropriate here because the client itself is not awaited — only its methods are async

## Tasks

<task type="auto">
  <name>Add Qdrant mock fixture to tests/conftest.py</name>
  <files>tests/conftest.py</files>
  <action>
    Add the following import at the top (alongside existing `AsyncMock, patch`):

    ```python
    from unittest.mock import AsyncMock, MagicMock, patch
    ```

    Then append a new fixture after `mock_payment_sdk`:

    ```python
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
    ```

    KEY POINTS:
    - Patch target is `"qdrant_client.AsyncQdrantClient"` — the class in the public module.
    - `return_value=MagicMock()` provides a permissive mock instance whose methods
      can be called without error (async methods return coroutines via `AsyncMock` auto-spec).
    - Since `app/db/qdrant.py` is imported before fixtures run, the patch must also
      cover the import-time instantiation — which it does because `patch` replaces the
      class in `qdrant_client` namespace before the module under test is re-evaluated.
    - No existing fixture changes; `mock_payment_sdk` is untouched.
  </action>
  <verify>pytest tests/ -v --tb=short</verify>
</task>

## Must-Haves

- [ ] `MagicMock` added to the `unittest.mock` import
- [ ] `mock_qdrant_client` fixture uses `autouse=True`
- [ ] Patch target is `"qdrant_client.AsyncQdrantClient"`
- [ ] `mock_payment_sdk` fixture is unchanged
- [ ] `pytest tests/ -v` — still 50/50 with no live network calls

## Success Criteria

- `pytest tests/ -v` — **50/50 passed, 0 failed** in < 5 s (proves no live TCP call to Qdrant)
