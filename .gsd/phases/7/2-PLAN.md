---
phase: 7
plan: 2
wave: 2
gap_closure: false
---

# Plan 7.2: Async Qdrant Client Module

## Objective

Create `app/db/qdrant.py` with a module-level `AsyncQdrantClient` singleton and a FastAPI dependency function `get_qdrant()`.

## Context

- `app/db/` — does not exist; must be created with `__init__.py`
- `qdrant_client.AsyncQdrantClient` constructor:
  `AsyncQdrantClient(url=..., api_key=...)` where `url=":memory:"` needs no network
- FastAPI `Depends(get_qdrant)` is the injection pattern; `get_qdrant` must be a plain function returning the singleton (not a generator, for a shared singleton)

## Tasks

<task type="auto">
  <name>Create app/db/__init__.py</name>
  <files>app/db/__init__.py</files>
  <action>Empty file.</action>
</task>

<task type="auto">
  <name>Create app/db/qdrant.py</name>
  <files>app/db/qdrant.py</files>
  <action>
    ```python
    from __future__ import annotations

    from qdrant_client import AsyncQdrantClient

    from app.core.config import settings


    _client: AsyncQdrantClient = AsyncQdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
    )


    def get_qdrant() -> AsyncQdrantClient:
        """FastAPI dependency — returns the shared async Qdrant client.

        Routers inject this via Depends(get_qdrant).
        In tests the client is mocked globally via conftest.py.
        """
        return _client
    ```

    KEY POINTS:
    - `_client` is a module-level singleton; created once at import time.
    - default `url=":memory:"` → no TCP socket, no connection errors in dev/test.
    - `api_key=None` is fine for `:memory:` and unauthenticated local instances.
    - `get_qdrant()` is a plain function (not an async generator) because the
      singleton is already initialised — no setup/teardown needed per request.
  </action>
  <verify>python -c "from app.db.qdrant import get_qdrant; print(type(get_qdrant()))"</verify>
</task>

## Must-Haves

- [ ] `app/db/__init__.py` exists
- [ ] `app/db/qdrant.py` exports `get_qdrant` and the `_client` singleton
- [ ] `get_qdrant()` is importable and returns an `AsyncQdrantClient` instance
- [ ] No network call made during import (`:memory:` default)

## Success Criteria

- `python -c "from app.db.qdrant import get_qdrant; print(type(get_qdrant()))"` →
  `<class 'qdrant_client.async_qdrant_client.AsyncQdrantClient'>`
- `pytest tests/ -v` — still 50/50
