---
phase: 8
plan: 1
wave: 1
gap_closure: false
---

# Plan 8.1: Dependencies & Config

## Objective

Add `slowapi` to `requirements.txt` and initialise a shared `Limiter` instance in
`app/core/config.py` so that every other module can import it without circular
dependencies.

## Context

- `requirements.txt` — currently pinned at `qdrant-client==1.11.3`; 10 deps total
- `app/core/config.py` — `Settings` currently has 7 fields; `masumi_config` singleton at
  the module level; **no** rate-limiter object yet
- `slowapi` wraps `limits` and integrates into Starlette/FastAPI via middleware +
  `@limiter.limit(...)` decorators on route functions

## Tasks

<task type="auto">
  <name>Add slowapi to requirements.txt</name>
  <files>requirements.txt</files>
  <action>
    Append one line after `qdrant-client==1.11.3`:

    ```
    slowapi>=0.1.9
    ```
  </action>
  <verify>pip install -r requirements.txt --dry-run 2>&1 | findstr /C:"slowapi"</verify>
</task>

<task type="auto">
  <name>Create Limiter singleton in app/core/config.py</name>
  <files>app/core/config.py</files>
  <action>
    Add the following import near the top of the file (after existing imports):

    ```python
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    ```

    Then append a module-level singleton **below** the existing `masumi_config` object:

    ```python
    limiter = Limiter(key_func=get_remote_address)
    ```

    KEY POINTS:
    - `get_remote_address` extracts the client IP from `request.client.host`;
      it is the canonical key function for IP-based rate limiting in slowapi.
    - The `Limiter` object is created once at import time and re-used everywhere.
    - No other lines in config.py change.
  </action>
  <verify>python -c "from app.core.config import limiter; print(type(limiter))"</verify>
</task>

## Must-Haves

- [ ] `slowapi>=0.1.9` in `requirements.txt`
- [ ] `limiter` available as `from app.core.config import limiter`
- [ ] `type(limiter)` prints `<class 'slowapi.Limiter'>`
- [ ] No existing `Settings` or `masumi_config` lines broken
- [ ] `pytest tests/ -v` — still 50/50

## Success Criteria

- `python -c "from app.core.config import limiter; print(type(limiter))"` → `<class 'slowapi.Limiter'>`
- `pip show slowapi` → installed, version ≥ 0.1.9
