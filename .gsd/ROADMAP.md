# ROADMAP.md — Masumi MIP-003 API Gateway

## Phases

| # | Name | Status | Description |
|---|------|--------|-------------|
| 1 | Domain Models & State Machine | ✅ COMPLETE | Pure domain layer: Pydantic v2 models, JobStatus enum, LEGAL_TRANSITIONS, validate_transition(), custom exceptions. No I/O, no HTTP. |
| 2 | In-Memory Repository | ✅ COMPLETE | Thread-safe InMemoryJobRepository with create/get/update_status. Job service layer. No HTTP. |
| 3 | Core Endpoints & Hashing | ✅ COMPLETE | FastAPI app factory, SHA-256 hash_inputs(), /availability, /input_schema, /start_job. Dependency injection via app.state. |
| 4 | Status, Input & Error Handling | ✅ COMPLETE | /status, /provide_input, mock Ed25519 verify_signature(), global exception handlers for all domain errors. |

## Phase Detail

### Phase 1: Domain Models & State Machine
**Files:**
- `app/domain/__init__.py`
- `app/domain/models.py`
- `app/domain/exceptions.py`

**Gate:** `pytest tests/test_phase1_models.py` → 6/6

---

### Phase 2: In-Memory Repository
**Files:**
- `app/repository/__init__.py`
- `app/repository/job_repo.py`
- `app/services/__init__.py`
- `app/services/job_service.py`

**Gate:** `pytest tests/test_phase2_repository.py` → 8/8

---

### Phase 3: Core Endpoints & Hashing
**Files:**
- `app/utils/__init__.py`
- `app/utils/hashing.py`
- `app/schemas/__init__.py`
- `app/schemas/requests.py`
- `app/routers/__init__.py`
- `app/routers/jobs.py`
- `app/main.py`

**Gate:** `pytest tests/test_phase3_endpoints.py` → 8/8

---

### Phase 4: Status, Input & Error Handling
**Files (additions):**
- `app/utils/signatures.py`
- `app/schemas/requests.py` (ProvideInputRequest added)
- `app/routers/jobs.py` (/status, /provide_input added)
- `app/main.py` (exception handlers added)

**Gate:** `pytest tests/test_phase4_full_flow.py` → 8/8 AND `pytest tests/` → 30/30
