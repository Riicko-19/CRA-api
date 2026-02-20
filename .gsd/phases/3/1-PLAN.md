---
phase: 3
plan: 1
wave: 1
gap_closure: false
---

# Plan 3.1: Hashing Utility & Request Schemas

## Objective

Implement the deterministic SHA-256 hashing utility and the `StartJobRequest` Pydantic schema. Pure Python — no FastAPI, no I/O. These are the building blocks for the router in Plan 3.2.

## Context

Load these files for context:
- `.gsd/CONTEXT.md` → Sections: "Hashing Contract"
- `.gsd/PHASE_3.md` → `app/utils/hashing.py`, `app/schemas/requests.py`
- `app/domain/models.py` — Pydantic v2 patterns to follow

## Tasks

<task type="auto">
  <name>Create app/utils/__init__.py and app/utils/hashing.py</name>
  <files>app/utils/__init__.py, app/utils/hashing.py</files>
  <action>
    1. Create `app/utils/__init__.py` as a completely empty file.

    2. Create `app/utils/hashing.py` with exactly this implementation:

    ```python
    import hashlib
    import json


    def hash_inputs(payload: dict) -> str:
        """
        Deterministic SHA-256 of a dict.
        sort_keys=True ensures field order independence.
        separators=(',', ':') eliminates whitespace variation.
        """
        canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    ```

    AVOID:
    - Do NOT import anything except `hashlib` and `json` — both are stdlib.
    - Do NOT use `hashlib.md5`, `hashlib.sha1`, or any other algorithm — must be `sha256`.
    - Do NOT add caching, memoization, or any side effects.
    - Do NOT use `json.dumps(payload)` without `sort_keys=True` and `separators=(',', ':')` — both are required for determinism.
    - The encoding MUST be `'utf-8'`.
  </action>
  <verify>python -c "from app.utils.hashing import hash_inputs; h=hash_inputs({'b':2,'a':1}); assert h==hash_inputs({'a':1,'b':2}); assert len(h)==64; print('hashing OK', h[:16])"</verify>
  <done>
    - `app/utils/__init__.py` exists and is empty.
    - `app/utils/hashing.py` imports cleanly.
    - `hash_inputs({'b':2,'a':1}) == hash_inputs({'a':1,'b':2})` — ordering independent.
    - `len(hash_inputs({})) == 64` — SHA-256 hex is always 64 chars.
    - Only `hashlib` and `json` imported (zero external deps).
  </done>
</task>

<task type="auto">
  <name>Create app/schemas/__init__.py and app/schemas/requests.py</name>
  <files>app/schemas/__init__.py, app/schemas/requests.py</files>
  <action>
    1. Create `app/schemas/__init__.py` as a completely empty file.

    2. Create `app/schemas/requests.py` with exactly this:

    ```python
    from typing import Any

    from pydantic import BaseModel, ConfigDict


    class StartJobRequest(BaseModel):
        model_config = ConfigDict(extra='forbid')

        inputs: dict[str, Any]
    ```

    AVOID:
    - Do NOT use `extra='allow'` or `extra='ignore'` — must be `'forbid'` so extra fields return 422.
    - Do NOT add any other fields, validators, or methods.
    - Do NOT import `fastapi` here — this is a pure Pydantic schema file.
    - Do NOT use `str | None` or other Python 3.10+ union syntax in type hints — use `Optional[X]` for optional fields.
  </action>
  <verify>python -c "from app.schemas.requests import StartJobRequest; r=StartJobRequest(inputs={'task':'x'}); print('schema OK', r.inputs)"</verify>
  <done>
    - `app/schemas/__init__.py` exists and is empty.
    - `app/schemas/requests.py` imports cleanly.
    - `StartJobRequest(inputs={'task': 'x'})` succeeds.
    - `StartJobRequest(inputs={}, EXTRA='bad')` raises `ValidationError`.
    - `StartJobRequest.model_json_schema()` returns a dict with `"type": "object"` and `"properties"` key.
  </done>
</task>

## Must-Haves

- [ ] `app/utils/__init__.py` exists (empty)
- [ ] `app/utils/hashing.py` — `hash_inputs()` using only `hashlib` + `json` stdlib
- [ ] `app/schemas/__init__.py` exists (empty)
- [ ] `app/schemas/requests.py` — `StartJobRequest` with `extra='forbid'`, single `inputs` field
- [ ] Zero external dependencies across both files

## Success Criteria

- [ ] `hash_inputs({'b':2,'a':1}) == hash_inputs({'a':1,'b':2})` — determinism verified
- [ ] `len(hash_inputs({})) == 64` — SHA-256 output length verified
- [ ] `StartJobRequest(inputs={}, EXTRA='x')` raises `ValidationError`
- [ ] `StartJobRequest.model_json_schema()` returns dict with `"type": "object"`
- [ ] All tasks verified passing
