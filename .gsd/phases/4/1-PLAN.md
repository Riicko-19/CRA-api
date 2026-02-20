---
phase: 4
plan: 1
wave: 1
gap_closure: false
---

# Plan 4.1: ProvideInputRequest Schema & Signature Verifier

## Objective

Extend the request schemas with `ProvideInputRequest` and create the mock Ed25519 signature verifier. Pure Python — no HTTP, no FastAPI. These are the last domain-adjacent helpers before wiring into the router.

## Context

Load these files for context:
- `.gsd/CONTEXT.md` → Sections: "Error Handling", "Job Lifecycle"
- `.gsd/PHASE_4.md` → `app/schemas/requests.py`, `app/utils/signatures.py`
- `app/schemas/requests.py` (Phase 3 — contains `StartJobRequest`)
- `app/domain/exceptions.py` (Phase 1 — contains `InvalidSignatureError`)

## Tasks

<task type="auto">
  <name>Add ProvideInputRequest to app/schemas/requests.py</name>
  <files>app/schemas/requests.py</files>
  <action>
    Extend `app/schemas/requests.py` by ADDING `ProvideInputRequest` after the existing `StartJobRequest` class. Do NOT remove or modify `StartJobRequest`.

    The final file must contain BOTH classes:

    ```python
    from typing import Any

    from pydantic import BaseModel, ConfigDict


    class StartJobRequest(BaseModel):
        model_config = ConfigDict(extra='forbid')

        inputs: dict[str, Any]


    class ProvideInputRequest(BaseModel):
        model_config = ConfigDict(extra='forbid')

        job_id: str
        signature: str
        data: dict[str, Any]
    ```

    AVOID:
    - Do NOT remove or modify `StartJobRequest` — Phase 3 tests depend on it.
    - `extra='forbid'` on `ProvideInputRequest` — extra fields must cause 422.
    - All 3 fields are required — no Optional, no defaults.
    - Do NOT import fastapi here — pure Pydantic only.
  </action>
  <verify>python -c "from app.schemas.requests import StartJobRequest, ProvideInputRequest; r=ProvideInputRequest(job_id='j1', signature='s1', data={'k':'v'}); print('schema OK', r.job_id)"</verify>
  <done>
    - `from app.schemas.requests import StartJobRequest, ProvideInputRequest` works.
    - `ProvideInputRequest(job_id='j1', signature='s1', data={})` succeeds.
    - `ProvideInputRequest(job_id='j1', signature='s1', data={}, evil='x')` raises `ValidationError`.
    - `StartJobRequest` still works — no regression.
  </done>
</task>

<task type="auto">
  <name>Create app/utils/signatures.py</name>
  <files>app/utils/signatures.py</files>
  <action>
    Create `app/utils/signatures.py` with exactly this implementation:

    ```python
    from app.domain.exceptions import InvalidSignatureError


    def verify_signature(job_id: str, signature: str) -> None:
        """
        Mock Ed25519 verification.
        A real implementation would use cryptography.hazmat.
        Contract: signature MUST equal "valid_sig_" + job_id
        Raises InvalidSignatureError on mismatch.
        """
        expected = f"valid_sig_{job_id}"
        if signature != expected:
            raise InvalidSignatureError(f"Signature mismatch for job {job_id!r}")
    ```

    AVOID:
    - Do NOT import `cryptography`, `nacl`, or any external crypto library — this is a mock.
    - Return type MUST be `None` — the function either passes silently or raises.
    - Raise `InvalidSignatureError` (from `app.domain.exceptions`) — NOT `HTTPException`.
    - Do NOT add caching or state — pure function, no side effects.
    - The check is `signature != f"valid_sig_{job_id}"` — exact string equality, no hashing.
  </action>
  <verify>python -c "from app.utils.signatures import verify_signature; verify_signature('j1', 'valid_sig_j1'); print('sig OK')"</verify>
  <done>
    - `verify_signature('j1', 'valid_sig_j1')` returns `None` (no exception).
    - `verify_signature('j1', 'wrong_sig')` raises `InvalidSignatureError`.
    - `verify_signature('abc', 'valid_sig_xyz')` raises `InvalidSignatureError` (ID must match).
    - No external imports — only `app.domain.exceptions`.
  </done>
</task>

## Must-Haves

- [ ] `app/schemas/requests.py` — BOTH `StartJobRequest` AND `ProvideInputRequest` present
- [ ] `ProvideInputRequest` has `extra='forbid'`, fields: `job_id: str`, `signature: str`, `data: dict[str, Any]`
- [ ] `app/utils/signatures.py` — `verify_signature()`, raises `InvalidSignatureError` on mismatch
- [ ] No external crypto dependencies — mock only

## Success Criteria

- [ ] `from app.schemas.requests import StartJobRequest, ProvideInputRequest` exits 0
- [ ] `verify_signature('j', 'valid_sig_j')` passes silently
- [ ] `verify_signature('j', 'bad')` raises `InvalidSignatureError`
