---
phase: 7
plan: 1
wave: 1
gap_closure: false
---

# Plan 7.1: Dependencies & Config

## Objective

Add `qdrant-client` to `requirements.txt` and extend `Settings(BaseSettings)` in `app/core/config.py` with two new Qdrant connection fields.

## Context

- `requirements.txt` — currently 9 deps; `qdrant-client` not present
- `app/core/config.py` — `Settings` currently has 5 fields (masumi only)
- `qdrant-client>=1.7` ships the async client as `qdrant_client.AsyncQdrantClient`

## Tasks

<task type="auto">
  <name>Add qdrant-client to requirements.txt</name>
  <files>requirements.txt</files>
  <action>
    Append one line:

    ```
    qdrant-client>=1.9.0
    ```
  </action>
  <verify>pip install -r requirements.txt --dry-run</verify>
</task>

<task type="auto">
  <name>Extend Settings in app/core/config.py</name>
  <files>app/core/config.py</files>
  <action>
    Add two new fields to `Settings(BaseSettings)`:

    ```python
    qdrant_url: str = ":memory:"
    qdrant_api_key: str | None = None
    ```

    KEY POINTS:
    - `qdrant_url = ":memory:"` is the in-memory default — safe for local dev and tests.
    - `qdrant_api_key = None` is correct for unauthenticated / local Qdrant instances.
    - Production sets `QDRANT_URL` and `QDRANT_API_KEY` env vars; no code changes required.
    - No other lines change; `masumi_config` singleton stays untouched.
  </action>
  <verify>python -c "from app.core.config import settings; print(settings.qdrant_url)"</verify>
</task>

## Must-Haves

- [ ] `qdrant-client>=1.9.0` in `requirements.txt`
- [ ] `settings.qdrant_url` defaults to `":memory:"`
- [ ] `settings.qdrant_api_key` defaults to `None`
- [ ] No existing `masumi_config` lines broken
- [ ] `pytest tests/ -v` — still 50/50

## Success Criteria

- `python -c "from app.core.config import settings; print(settings.qdrant_url)"` → `:memory:`
- `pip show qdrant-client` → version ≥ 1.9.0
