# SPEC.md — Masumi MIP-003 API Gateway

> **Status**: `FINALIZED`
>
> ⚠️ **Planning Lock**: No code may be written until this spec is marked `FINALIZED`.

## Vision

A Masumi MIP-003 compliant API Gateway that enables an AI agent to be listed on Sukosumi, securely accept and process paid jobs, execute tasks deterministically, and return verifiable results. The system is built on the axioms: Strict > Flexible, Predictable > Intelligent, Secure > Fast, Deterministic > Dynamic.

## Goals

1. **MIP-003 Compliance** — Expose the canonical Masumi endpoints (`/availability`, `/input_schema`, `/start_job`, `/status`, `/provide_input`)
2. **Strict Domain Integrity** — Pydantic v2 with `extra='forbid'` + frozen models; no silent data coercion
3. **Deterministic Hashing** — SHA-256 canonical input hashing (stdlib only) for verifiable, reproducible job fingerprints
4. **Safe State Machine** — Thread-safe, in-memory repository that strictly guards illegal job lifecycle transitions

## Non-Goals (Out of Scope)

- Real blockchain integration (all `blockchain_identifier` values are mock)
- Real Ed25519 cryptographic signature verification (mock contract only)
- Database persistence (in-memory store only in MVP)
- Authentication/authorization beyond signature mock

## Constraints

- Python 3.10+ only
- FastAPI (latest stable) + Pydantic v2
- `hashlib` and `json` from stdlib only — no external crypto dependencies
- All `Job` models are frozen (immutable after creation)
- Thread-safety via `threading.Lock` — no async locking

## Success Criteria

- [ ] `pytest tests/test_phase1_models.py` → 6/6 PASSED
- [ ] `pytest tests/test_phase2_repository.py` → 8/8 PASSED
- [ ] `pytest tests/test_phase3_endpoints.py` → 8/8 PASSED
- [ ] `pytest tests/test_phase4_full_flow.py` → 8/8 PASSED
- [ ] `pytest tests/` (all) → 30/30 PASSED, 0 FAILED
- [ ] No FastAPI imports in `domain/` or `repository/` layers

---

*Last updated: 2026-02-20*
